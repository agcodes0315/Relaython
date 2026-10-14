import os
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError


REGION = os.environ.get(
    "AWS_REGION",
    "us-west-2",
)

TASKS_TABLE = os.environ.get(
    "RELAY_TASKS_TABLE",
    "RelayTasks",
)

AUDIT_TABLE = os.environ.get(
    "RELAY_AUDIT_TABLE",
    "RelayAudit",
)


dynamodb = boto3.resource(
    "dynamodb",
    region_name=REGION,
)

tasks_table = dynamodb.Table(
    TASKS_TABLE
)

audit_table = dynamodb.Table(
    AUDIT_TABLE
)


def _event_id() -> str:
    now = datetime.now(
        timezone.utc
    )

    return (
        now.strftime(
            "%Y%m%dT%H%M%S%fZ"
        )
        + "-"
        + str(uuid4())
    )


def _write_audit(
    task_id: str,
    event_type: str,
    details: dict,
) -> None:
    now = datetime.now(
        timezone.utc
    )

    audit_table.put_item(
        Item={
            "task_id": task_id,
            "event_id": _event_id(),
            "event_type": event_type,
            "timestamp": now.isoformat(),
            "details": details,
        }
    )


SCAM_AWAITING = "AWAITING_FAMILY"


def _safe_text(value) -> str:
    """Short text for logs and audit details. Never the whole object."""
    return str(value)[:40]


def _scam_response(
    task_id: str,
    step,
    result: str,
) -> dict:
    return {
        "statusCode": 200,
        "task_id": task_id,
        "step": step if isinstance(step, str) else None,
        "result": result,
    }


def _is_condition_failure(exc: ClientError) -> bool:
    return (
        exc.response
        .get("Error", {})
        .get("Code")
        == "ConditionalCheckFailedException"
    )


def _order_key(contact: dict) -> float:
    try:
        return float(contact.get("order", 10**9))
    except (TypeError, ValueError):
        return float(10**9)


def _ordered_contacts(task: dict) -> list[dict]:
    """Trusted contacts sorted by their 'order' field, not list position."""
    contacts = task.get("contacts")

    if not isinstance(contacts, list):
        return []

    usable = [
        contact
        for contact in contacts
        if isinstance(contact, dict)
        and contact.get("contact_id")
    ]

    usable.sort(key=_order_key)

    return usable


def _scam_escalate(
    task_id: str,
    task: dict,
    event: dict,
    now_iso: str,
) -> dict:
    """Timer step: ask the next trusted contact. Idempotent."""
    to_index = event.get("to_index")

    if (
        isinstance(to_index, bool)
        or not isinstance(to_index, int)
        or to_index < 1
    ):
        _write_audit(
            task_id,
            "ESCALATE_SKIPPED",
            {"reason": "invalid to_index"},
        )

        return _scam_response(
            task_id, "ESCALATE", "skipped"
        )

    contacts = _ordered_contacts(task)

    if to_index >= len(contacts):
        _write_audit(
            task_id,
            "ESCALATE_SKIPPED",
            {
                "reason": "no contact at that position",
                "to_index": to_index,
            },
        )

        return _scam_response(
            task_id, "ESCALATE", "skipped"
        )

    # Default-deny: without a deadline or an approvals map we cannot
    # issue a valid approval entry, so we issue nothing.
    if not task.get("hold_expires_at"):
        _write_audit(
            task_id,
            "ESCALATE_SKIPPED",
            {"reason": "case has no hold_expires_at"},
        )

        return _scam_response(
            task_id, "ESCALATE", "skipped"
        )

    if not isinstance(task.get("approvals"), dict):
        _write_audit(
            task_id,
            "ESCALATE_SKIPPED",
            {"reason": "case has no approvals map"},
        )

        return _scam_response(
            task_id, "ESCALATE", "skipped"
        )

    from_contact_id = str(
        contacts[to_index - 1]["contact_id"]
    )

    to_contact_id = str(
        contacts[to_index]["contact_id"]
    )

    entry = {
        "issued_at": now_iso,
        "expires_at": task["hold_expires_at"],
        "used": False,
        "attempts": 0,
    }

    try:
        tasks_table.update_item(
            Key={
                "task_id": task_id
            },
            UpdateExpression=(
                "SET current_contact_index = :k, "
                "approvals.#cid = :entry"
            ),
            ConditionExpression=(
                "#s = :awaiting "
                "AND current_contact_index = :prev"
            ),
            ExpressionAttributeNames={
                "#s": "status",
                "#cid": to_contact_id,
            },
            ExpressionAttributeValues={
                ":awaiting": SCAM_AWAITING,
                ":prev": to_index - 1,
                ":k": to_index,
                ":entry": entry,
            },
        )

    except ClientError as exc:
        if not _is_condition_failure(exc):
            raise

        _write_audit(
            task_id,
            "ESCALATE_SKIPPED",
            {
                "reason": (
                    "already decided "
                    "or already escalated"
                ),
                "to_index": to_index,
            },
        )

        return _scam_response(
            task_id, "ESCALATE", "skipped"
        )

    _write_audit(
        task_id,
        "ESCALATED",
        {
            "from_contact_id": from_contact_id,
            "to_contact_id": to_contact_id,
            "to_index": to_index,
        },
    )

    return _scam_response(
        task_id, "ESCALATE", "applied"
    )


def _scam_expire(
    task_id: str,
    task: dict,
    now_iso: str,
) -> dict:
    """Timer step: nobody answered in time, so the payment stays blocked.

    This only ever blocks. It never lets a payment go through.
    """
    try:
        tasks_table.update_item(
            Key={
                "task_id": task_id
            },
            UpdateExpression=(
                "SET #s = :expired, "
                "payment_status = :blocked, "
                "approved = :no, "
                "decided_at = :now"
            ),
            ConditionExpression="#s = :awaiting",
            ExpressionAttributeNames={
                "#s": "status",
            },
            ExpressionAttributeValues={
                ":expired": "EXPIRED_BLOCKED",
                ":awaiting": SCAM_AWAITING,
                ":blocked": "BLOCKED",
                ":no": False,
                ":now": now_iso,
            },
        )

    except ClientError as exc:
        if not _is_condition_failure(exc):
            raise

        _write_audit(
            task_id,
            "EXPIRE_SKIPPED",
            {
                "reason": "case already decided",
                "status_when_woken": _safe_text(
                    task.get("status")
                ),
            },
        )

        return _scam_response(
            task_id, "EXPIRE", "skipped"
        )

    _write_audit(
        task_id,
        "HOLD_EXPIRED",
        {
            "hold_expires_at": task.get(
                "hold_expires_at"
            ),
            "message": (
                "No family decision before "
                "the deadline. The payment "
                "stays blocked."
            ),
        },
    )

    _write_audit(
        task_id,
        "PAYMENT_BLOCKED",
        {
            "payment_status": "BLOCKED",
            "reason": (
                "hold expired without "
                "a family decision"
            ),
        },
    )

    return _scam_response(
        task_id, "EXPIRE", "applied"
    )


def _handle_scam_case(
    task_id: str,
    task: dict,
    event: dict,
) -> dict:
    """Relay Shield timer wake-up. Only ESCALATE and EXPIRE are handled."""
    step = event.get("step")

    now_iso = datetime.now(
        timezone.utc
    ).isoformat()

    if step == "ESCALATE":
        result = _scam_escalate(
            task_id,
            task,
            event,
            now_iso,
        )

    elif step == "EXPIRE":
        result = _scam_expire(
            task_id,
            task,
            now_iso,
        )

    else:
        _write_audit(
            task_id,
            "SCAM_WAKE_IGNORED",
            {
                "reason": "unknown or missing step",
                "step": _safe_text(step),
            },
        )

        result = _scam_response(
            task_id, step, "ignored"
        )

    print(
        "Relay shield wake handled:",
        task_id,
        _safe_text(step),
        result["result"],
    )

    return result


def lambda_handler(
    event,
    context,
):
    if not isinstance(event, dict):
        event = {}

    task_id = event.get(
        "task_id"
    )

    # Log only the task id and the step. Never print the whole event:
    # it can carry case data.
    print(
        "Relay resume worker invoked. task_id:",
        task_id,
        "step:",
        _safe_text(event.get("step")),
    )

    if not task_id:
        return {
            "statusCode": 400,
            "message": (
                "task_id is required"
            ),
        }

    response = tasks_table.get_item(
        Key={
            "task_id": task_id
        }
    )

    task = response.get(
        "Item"
    )

    if task is None:
        return {
            "statusCode": 404,
            "task_id": task_id,
            "message": (
                "Relay task not found"
            ),
        }

    if task.get("kind") == "scam_case":
        return _handle_scam_case(
            task_id,
            task,
            event,
        )

    now = datetime.now(
        timezone.utc
    )

    now_iso = now.isoformat()

    _write_audit(
        task_id,
        "RESUME_TRIGGERED",
        {
            "source": (
                "EventBridge Scheduler"
            ),
            "current_status": (
                task.get(
                    "status",
                    "UNKNOWN",
                )
            ),
            "message": (
                "Relay was automatically "
                "woken to inspect this "
                "durable task."
            ),
        },
    )

    selected_provider = task.get(
        "selected_provider"
    )

    selected_provider_id = None

    if isinstance(
        selected_provider,
        dict,
    ):
        selected_provider_id = (
            selected_provider.get(
                "provider_id"
            )
        )

    _write_audit(
        task_id,
        "STATE_RESTORED",
        {
            "goal": task.get(
                "goal"
            ),
            "budget": task.get(
                "budget"
            ),
            "deadline": task.get(
                "deadline"
            ),
            "excluded_days": task.get(
                "excluded_days",
                [],
            ),
            "current_status": (
                task.get(
                    "status",
                    "UNKNOWN",
                )
            ),
            "selected_provider_id": (
                selected_provider_id
            ),
            "approved": task.get(
                "approved",
                False,
            ),
        },
    )

    updated = tasks_table.update_item(
        Key={
            "task_id": task_id
        },
        UpdateExpression=(
            "SET "
            "last_resumed_at = :now, "
            "last_resume_source = :source, "
            "wait_status = :status "
            "ADD resume_count :one"
        ),
        ExpressionAttributeValues={
            ":now": now_iso,
            ":source": (
                "EventBridge Scheduler"
            ),
            ":status": "RESUMED",
            ":one": 1,
        },
        ReturnValues="ALL_NEW",
    )

    resumed_task = updated[
        "Attributes"
    ]

    _write_audit(
        task_id,
        "TASK_RESUMED",
        {
            "resume_count": (
                resumed_task.get(
                    "resume_count",
                    1,
                )
            ),
            "business_status": (
                resumed_task.get(
                    "status",
                    "UNKNOWN",
                )
            ),
            "message": (
                "Relay restored the "
                "persisted task without "
                "changing its business "
                "constraints or approval "
                "state."
            ),
        },
    )

    print(
        "Relay task resumed:",
        task_id,
    )

    return {
        "statusCode": 200,
        "task_id": task_id,
        "task_status": (
            resumed_task.get(
                "status"
            )
        ),
        "wait_status": (
            resumed_task.get(
                "wait_status"
            )
        ),
        "resume_count": (
            resumed_task.get(
                "resume_count"
            )
        ),
        "last_resumed_at": (
            resumed_task.get(
                "last_resumed_at"
            )
        ),
        "message": (
            "Relay restored and resumed "
            "the durable task."
        ),
    }