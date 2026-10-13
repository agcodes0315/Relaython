from __future__ import annotations
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from botocore.exceptions import ClientError
from relay.audit import record_event
from relay.store import (
    _from_decimal,
    _to_decimal,
    get_task,
    save_task,
    tasks_table,
)
from relay.scam.data import get_profile
from relay.scam.policy import (
    assess_payment,
    validate_case_transition,
)
from relay.scam.scoring import level_for, mask_digits
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
def _conditional_update(
    case_id: str,
    expected_status: str,
    set_values: dict,
    extra_condition: str | None = None,
    extra_names: dict | None = None,
    extra_values: dict | None = None,
) -> dict | None:
    """
    Atomically update a case only when it is still in the expected state.
    This prevents concurrent family decisions or timer events from silently
    overwriting one another.
    """
    expression_names: dict[str, str] = {
        "#s": "status",
    }
    expression_values: dict[str, object] = {
        ":expected_status": expected_status,
    }
    assignments: list[str] = []
    for index, (key, value) in enumerate(set_values.items()):
        name_key = f"#n{index}"
        value_key = f":v{index}"

        expression_names[name_key] = key
        expression_values[value_key] = _to_decimal(value)

        assignments.append(
            f"{name_key} = {value_key}"
        )

    if extra_names:
        expression_names.update(extra_names)

    if extra_values:
        for key, value in extra_values.items():
            expression_values[key] = _to_decimal(value)
    condition = "#s = :expected_status"
    if extra_condition:
        condition = (
            f"({condition}) AND "
            f"({extra_condition})"
        )
    try:
        response = tasks_table.update_item(
            Key={
                "task_id": case_id,
            },
            UpdateExpression=(
                "SET " + ", ".join(assignments)
            ),
            ConditionExpression=condition,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        code = (
            exc.response
            .get("Error", {})
            .get("Code")
        )

        if code == "ConditionalCheckFailedException":
            return None

        raise
    item = response.get("Attributes")

    if item is None:
        return None

    return _from_decimal(item)
def _clamp_cooling_minutes(
    requested: int | None,
    profile: dict,
) -> int:
    if requested is None:
        requested = int(
            profile.get(
                "cooling_off_minutes",
                30,
            )
        )
    try:
        value = int(requested)
    except (TypeError, ValueError):
        value = int(
            profile.get(
                "cooling_off_minutes",
                30,
            )
        )

    return max(
        2,
        min(60, value),
    )
def _safe_contacts(profile: dict) -> list[dict]:
    contacts = []

    for contact in profile.get("contacts", []):
        if not isinstance(contact, dict):
            continue

        contacts.append(
            {
                "contact_id": contact.get(
                    "contact_id"
                ),
                "name": contact.get("name"),
                "order": contact.get("order"),
            }
        )

    contacts.sort(
        key=lambda value: value.get(
            "order",
            10**9,
        )
    )
    return contacts
def open_protection_case_logic(
    owner_id: str,
    risk_score: int,
    amount: float | None,
    payee_label: str,
    payee_is_new: bool,
    signals: list[str] | None = None,
    cooling_off_minutes: int | None = None,
) -> dict:
    profile = get_profile(owner_id)

    if profile is None:
        return {
            "error": "Unknown protected user",
        }

    decision_result = assess_payment(
        risk_score=risk_score,
        amount=amount,
        payee_is_new=payee_is_new,
        profile=profile,
    )

    decision = decision_result["decision"]
    status_by_decision = {
        "ALLOW": "CLEARED",
        "WARN": "WARNED",
        "HOLD": "HELD",
        "BLOCK": "BLOCKED",
    }

    target_status = status_by_decision[
        decision
    ]

    transition_ok, transition_message = (
        validate_case_transition(
            "OPENED",
            target_status,
        )
    )

    if not transition_ok:
        return {
            "error": transition_message,
        }

    cooling_minutes = (
        _clamp_cooling_minutes(
            cooling_off_minutes,
            profile,
        )
    )
    created_at = _now_iso()

    masked_payee = mask_digits(
        "" if payee_label is None
        else str(payee_label)
    )

    signal_names = [
        str(signal)
        for signal in (signals or [])
    ]

    payment_status = "NONE"

    if decision == "HOLD":
        payment_status = "HELD"

    elif decision == "BLOCK":
        payment_status = "BLOCKED"

    case_id = f"case-{uuid4()}"

    case: dict = {
        "task_id": case_id,
        "kind": "scam_case",
        "owner_id": owner_id,
        "status": target_status,
        "risk_score": int(risk_score),
        "risk_level": level_for(
            risk_score
        ),
        "signals": signal_names,
        "amount": amount,
        "payee_label": masked_payee,
        "payee_is_new": bool(
            payee_is_new
        ),
        "decision": decision,
        "reasons": list(
            decision_result.get(
                "reasons",
                [],
            )
        ),
        "contacts": _safe_contacts(
            profile
        ),
        "current_contact_index": -1,
        "approvals": {},
        "cooling_off_minutes": (
            cooling_minutes
        ),
        "payment_status": payment_status,
        "created_at": created_at,
        "approved": False,
    }

    if decision == "HOLD":
        started_at = datetime.fromisoformat(
            created_at
        )

        expires_at = (
            started_at
            + timedelta(
                minutes=cooling_minutes
            )
        )

        case["hold_started_at"] = (
            started_at.isoformat()
        )

        case["hold_expires_at"] = (
            expires_at.isoformat()
        )

    save_task(case)

    record_event(
        case_id,
        "CASE_OPENED",
        {
            "status": target_status,
            "risk_score": int(
                risk_score
            ),
            "risk_level": level_for(
                risk_score
            ),
            "payee_label": masked_payee,
        },
    )

    record_event(
        case_id,
        "POLICY_EVALUATED",
        {
            "decision": decision,
            "reasons": list(
                decision_result.get(
                    "reasons",
                    [],
                )
            ),
        },
    )

    if decision == "HOLD":
        record_event(
            case_id,
            "PAYMENT_HELD",
            {
                "amount": amount,
                "payee_label": (
                    masked_payee
                ),
                "hold_expires_at": (
                    case[
                        "hold_expires_at"
                    ]
                ),
            },
        )

    return case
def get_protection_case_logic(
    case_id: str,
    owner_id: str,
) -> dict:
    case = get_task(case_id)

    # Deliberately use the exact same response for:
    # 1. nonexistent case
    # 2. real case owned by someone else
    # This prevents ownership enumeration.
    if (
        case is None
        or case.get("kind")
        != "scam_case"
        or case.get("owner_id")
        != owner_id
    ):
        return {
            "error": "Case not found",
        }
    return case