import os
from datetime import datetime, timezone
from uuid import uuid4

import boto3


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


def make_event_id():
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


def write_audit(
    task_id,
    event_type,
    details,
):
    now = datetime.now(
        timezone.utc
    )

    audit_table.put_item(
        Item={
            "task_id": task_id,
            "event_id": make_event_id(),
            "event_type": event_type,
            "timestamp": now.isoformat(),
            "details": details,
        }
    )


def lambda_handler(
    event,
    context,
):
    print(
        "Relay resume worker invoked."
    )

    print(event)

    task_id = event.get(
        "task_id"
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

    now = datetime.now(
        timezone.utc
    )

    now_iso = now.isoformat()

    write_audit(
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
        },
    )

    selected_provider = (
        task.get(
            "selected_provider"
        )
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

    write_audit(
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
            "excluded_days": (
                task.get(
                    "excluded_days",
                    [],
                )
            ),
            "business_status": (
                task.get(
                    "status",
                    "UNKNOWN",
                )
            ),
            "selected_provider_id": (
                selected_provider_id
            ),
            "approved": (
                task.get(
                    "approved",
                    False,
                )
            ),
        },
    )

    current_resume_count = int(
        task.get(
            "resume_count",
            0,
        )
    )

    new_resume_count = (
        current_resume_count + 1
    )

    tasks_table.update_item(
        Key={
            "task_id": task_id
        },
        UpdateExpression=(
            "SET "
            "last_resumed_at = :now, "
            "last_resume_source = :source, "
            "wait_status = :wait_status, "
            "resume_count = :resume_count"
        ),
        ExpressionAttributeValues={
            ":now": now_iso,
            ":source": (
                "EventBridge Scheduler"
            ),
            ":wait_status": (
                "RESUMED"
            ),
            ":resume_count": (
                new_resume_count
            ),
        },
    )

    write_audit(
        task_id,
        "TASK_RESUMED",
        {
            "resume_count": (
                new_resume_count
            ),
            "business_status": (
                task.get(
                    "status",
                    "UNKNOWN",
                )
            ),
            "message": (
                "Relay restored the "
                "persisted task and "
                "continued without "
                "losing context."
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
        "task_status": task.get(
            "status"
        ),
        "wait_status": "RESUMED",
        "resume_count": (
            new_resume_count
        ),
        "last_resumed_at": (
            now_iso
        ),
        "message": (
            "Relay restored and "
            "resumed the durable task."
        ),
    }
