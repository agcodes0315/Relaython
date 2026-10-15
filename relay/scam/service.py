from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from botocore.exceptions import ClientError

from relay.audit import get_task_events, record_event
from relay.scam.data import get_profile
from relay.scam.policy import (
    assess_payment,
    contact_at,
    validate_case_transition,
)
from relay.scam.receipt import build_case_receipt
from relay.scam.scoring import level_for, mask_digits
from relay.scam.tokens import is_expired, make_token, verify_token
from relay.scheduler import schedule_resume
from relay.store import (
    _from_decimal,
    _to_decimal,
    get_task,
    save_task,
    tasks_table,
)

MAX_WRONG_CODES = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _secret() -> str:
    """Server secret used to derive family approval codes."""
    value = os.environ.get("RELAY_SHIELD_SECRET")

    if not value:
        raise RuntimeError("RELAY_SHIELD_SECRET is not set")

    return value


# --------------------------------------------------------------------------
# Safe update helper
# --------------------------------------------------------------------------


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
    overwriting one another. 'status' is a DynamoDB reserved word, so it is
    always referenced through the #s placeholder.

    A key in set_values may be a dotted path such as 'approvals.c_rohan.used';
    every part of the path gets its own name placeholder.
    """
    expression_names: dict[str, str] = {"#s": "status"}
    expression_values: dict[str, object] = {
        ":expected_status": expected_status,
    }
    assignments: list[str] = []

    for index, (key, value) in enumerate(set_values.items()):
        value_key = f":v{index}"
        parts = str(key).split(".")
        path_parts = []

        for part_index, part in enumerate(parts):
            name_key = f"#n{index}_{part_index}" if len(parts) > 1 else f"#n{index}"
            expression_names[name_key] = part
            path_parts.append(name_key)

        expression_values[value_key] = _to_decimal(value)
        assignments.append(f"{'.'.join(path_parts)} = {value_key}")

    if extra_names:
        expression_names.update(extra_names)

    if extra_values:
        for key, value in extra_values.items():
            expression_values[key] = _to_decimal(value)

    condition = "#s = :expected_status"

    if extra_condition:
        condition = f"({condition}) AND ({extra_condition})"

    try:
        response = tasks_table.update_item(
            Key={"task_id": case_id},
            UpdateExpression="SET " + ", ".join(assignments),
            ConditionExpression=condition,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")

        if code == "ConditionalCheckFailedException":
            return None

        raise

    item = response.get("Attributes")

    if item is None:
        return None

    return _from_decimal(item)


def _register_wrong_code(case_id: str, contact_id: str) -> dict | None:
    """Count one wrong approval code for a contact (no status change).

    Locks the contact (used = True) once MAX_WRONG_CODES is reached.
    Returns {'attempts': n, 'locked': bool}, or None when the case is no
    longer awaiting this contact (already decided, or contact already used).
    """
    names = {"#s": "status", "#cid": contact_id}
    condition = "#s = :awaiting AND approvals.#cid.used = :false"

    try:
        response = tasks_table.update_item(
            Key={"task_id": case_id},
            UpdateExpression=(
                "SET approvals.#cid.attempts = "
                "if_not_exists(approvals.#cid.attempts, :zero) + :one"
            ),
            ConditionExpression=condition,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues={
                ":awaiting": "AWAITING_FAMILY",
                ":false": False,
                ":zero": 0,
                ":one": 1,
            },
            ReturnValues="ALL_NEW",
        )

        item = _from_decimal(response.get("Attributes") or {})
        attempts = int(item.get("approvals", {}).get(contact_id, {}).get("attempts", 0))
        locked = attempts >= MAX_WRONG_CODES

        if locked:
            tasks_table.update_item(
                Key={"task_id": case_id},
                UpdateExpression="SET approvals.#cid.used = :true",
                ConditionExpression=condition,
                ExpressionAttributeNames=names,
                ExpressionAttributeValues={
                    ":awaiting": "AWAITING_FAMILY",
                    ":false": False,
                    ":true": True,
                },
            )

        return {"attempts": attempts, "locked": locked}

    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")

        if code == "ConditionalCheckFailedException":
            return None

        raise


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _clamp_cooling_minutes(
    requested: int | None,
    profile: dict,
) -> int:
    if requested is None:
        requested = int(profile.get("cooling_off_minutes", 30))

    try:
        value = int(requested)
    except (TypeError, ValueError):
        value = int(profile.get("cooling_off_minutes", 30))

    return max(2, min(60, value))


def _safe_contacts(profile: dict) -> list[dict]:
    contacts = []

    for contact in profile.get("contacts", []):
        if not isinstance(contact, dict):
            continue

        contacts.append(
            {
                "contact_id": contact.get("contact_id"),
                "name": contact.get("name"),
                "order": contact.get("order"),
            }
        )

    contacts.sort(key=lambda value: value.get("order", 10**9))
    return contacts


def _owned_case(case_id: str, owner_id: str) -> dict | None:
    """Return the case only when it exists, is a scam case and belongs to owner.

    Callers answer 'Case not found' for every None, so a missing case and
    someone else's case look identical (no ownership enumeration).
    """
    case = get_task(case_id)

    if (
        case is None
        or case.get("kind") != "scam_case"
        or case.get("owner_id") != owner_id
    ):
        return None

    return case


def _contact_name(case: dict, contact_id: str) -> str | None:
    for contact in case.get("contacts") or []:
        if isinstance(contact, dict) and contact.get("contact_id") == contact_id:
            return contact.get("name")

    return None


def _active_entry(case: dict, contact_id: str) -> dict | None:
    """The approval entry for this contact if unused and not expired."""
    entry = (case.get("approvals") or {}).get(contact_id)

    if not isinstance(entry, dict) or entry.get("used"):
        return None

    try:
        if is_expired(entry.get("expires_at", "")):
            return None
    except (ValueError, TypeError, AttributeError):
        return None

    return entry


# --------------------------------------------------------------------------
# Task 5: open and read cases
# --------------------------------------------------------------------------


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
        return {"error": "Unknown protected user"}

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
    target_status = status_by_decision[decision]

    transition_ok, transition_message = validate_case_transition(
        "OPENED",
        target_status,
    )

    if not transition_ok:
        return {"error": transition_message}

    cooling_minutes = _clamp_cooling_minutes(cooling_off_minutes, profile)
    created_at = _now_iso()
    masked_payee = mask_digits("" if payee_label is None else str(payee_label))
    signal_names = [str(signal) for signal in (signals or [])]

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
        "risk_level": level_for(risk_score),
        "signals": signal_names,
        "amount": amount,
        "payee_label": masked_payee,
        "payee_is_new": bool(payee_is_new),
        "decision": decision,
        "reasons": list(decision_result.get("reasons", [])),
        "contacts": _safe_contacts(profile),
        "current_contact_index": -1,
        "approvals": {},
        "cooling_off_minutes": cooling_minutes,
        "payment_status": payment_status,
        "created_at": created_at,
        "approved": False,
    }

    if decision == "HOLD":
        started_at = datetime.fromisoformat(created_at)
        expires_at = started_at + timedelta(minutes=cooling_minutes)
        case["hold_started_at"] = started_at.isoformat()
        case["hold_expires_at"] = expires_at.isoformat()

    save_task(case)

    record_event(
        case_id,
        "CASE_OPENED",
        {
            "status": target_status,
            "risk_score": int(risk_score),
            "risk_level": level_for(risk_score),
            "payee_label": masked_payee,
        },
    )

    record_event(
        case_id,
        "POLICY_EVALUATED",
        {
            "decision": decision,
            "reasons": list(decision_result.get("reasons", [])),
        },
    )

    if decision == "HOLD":
        record_event(
            case_id,
            "PAYMENT_HELD",
            {
                "amount": amount,
                "payee_label": masked_payee,
                "hold_expires_at": case["hold_expires_at"],
            },
        )

        # A held payment must never sit without a family alert.
        alert = alert_trusted_contact_logic(case_id, owner_id)
        result = dict(case)

        if "alerted_contact" in alert:
            result["alerted_contact"] = alert["alerted_contact"]
            result["status"] = alert.get("status", result["status"])
        elif "error" in alert:
            result["alert_error"] = alert["error"]

        return result

    return case


def get_protection_case_logic(
    case_id: str,
    owner_id: str,
) -> dict:
    case = _owned_case(case_id, owner_id)

    # Deliberately the same response for a nonexistent case and for a real
    # case owned by someone else. This prevents ownership enumeration.
    if case is None:
        return {"error": "Case not found"}

    return case


# --------------------------------------------------------------------------
# Task 6: family alert, inbox, decision
# --------------------------------------------------------------------------


def _schedule_case_timers(case: dict) -> int:
    """Create escalation timers (one per later contact) plus the expiry timer.

    Returns how many timers failed to schedule. A failed timer never releases
    money: the payment simply stays held until a decision or a later expiry.
    """
    case_id = case["task_id"]
    contacts = case.get("contacts") or []
    count = max(1, len(contacts))
    started = datetime.fromisoformat(case["hold_started_at"])
    expires = datetime.fromisoformat(case["hold_expires_at"])
    total_minutes = float(case.get("cooling_off_minutes") or 2)
    step = max(1.0, total_minutes / count)
    failed = 0

    plan = [
        (f"e{k}", started + timedelta(minutes=k * step), {"step": "ESCALATE", "to_index": k})
        for k in range(1, count)
    ]
    plan.append(("exp", expires, {"step": "EXPIRE"}))

    for suffix, run_at, payload in plan:
        try:
            outcome = schedule_resume(
                case_id,
                run_at,
                name_suffix=suffix,
                extra_payload=payload,
                persist_task=False,
            )

            if isinstance(outcome, dict) and "error" in outcome:
                failed += 1
        except Exception:  # noqa: BLE001 - never let a timer failure raise
            failed += 1

    return failed


def alert_trusted_contact_logic(case_id: str, owner_id: str) -> dict:
    """Alert the first trusted contact (idempotent). Never returns the code."""
    _secret()  # fail closed: a hold nobody can approve is a misconfiguration

    case = _owned_case(case_id, owner_id)

    if case is None:
        return {"error": "Case not found"}

    status = case.get("status")

    if status == "AWAITING_FAMILY":
        return {"already_alerted": True, "status": status}

    if status != "HELD":
        return {"error": f"Case cannot be alerted while {status}"}

    contact = contact_at(case, 0)

    if contact is None:
        return {"error": "No trusted contact is configured"}

    contact_id = contact["contact_id"]
    now = _now_iso()
    entry = {
        "issued_at": now,
        "expires_at": case["hold_expires_at"],
        "used": False,
        "attempts": 0,
    }

    updated = _conditional_update(
        case_id,
        "HELD",
        {
            "status": "AWAITING_FAMILY",
            f"approvals.{contact_id}": entry,
            "current_contact_index": 0,
        },
        extra_condition="attribute_not_exists(approvals.#cid)",
        extra_names={"#cid": contact_id},
    )

    if updated is None:
        current = get_task(case_id) or {}
        return {
            "already_alerted": True,
            "status": current.get("status"),
        }

    record_event(
        case_id,
        "CONTACT_ALERTED",
        {"contact_id": contact_id, "name": contact.get("name")},
    )

    timers_failed = _schedule_case_timers(updated)

    return {
        "case_id": case_id,
        "status": updated.get("status", "AWAITING_FAMILY"),
        "alerted_contact": {
            "contact_id": contact_id,
            "name": contact.get("name"),
        },
        "hold_expires_at": updated.get("hold_expires_at"),
        "timers_failed": timers_failed,
        "message": (
            f"{contact.get('name')} was alerted. The payment stays on hold "
            "until a family member decides or the hold expires."
        ),
    }


def get_family_inbox_logic(case_id: str, contact_id: str) -> dict:
    """SIMULATION ONLY: stands in for an SMS or push message to the family
    member's phone. It is the only place an approval code is ever shown. In
    production the code would travel by SMS or push, not through MCP.
    """
    case = get_task(case_id)

    if (
        case is None
        or case.get("kind") != "scam_case"
        or case.get("status") != "AWAITING_FAMILY"
    ):
        return {"found": False}

    entry = _active_entry(case, contact_id)

    if entry is None:
        return {"found": False}

    code = make_token(_secret(), case_id, contact_id, entry["issued_at"])
    amount = case.get("amount")
    amount_text = (
        str(int(amount))
        if isinstance(amount, (int, float)) and float(amount).is_integer()
        else str(amount)
    )

    return {
        "found": True,
        "for": _contact_name(case, contact_id),
        "message": (
            f"Payment of Rs {amount_text} to {case.get('payee_label')} "
            "is on hold. Approve or reject."
        ),
        "approval_code": code,
    }


def record_family_decision_logic(
    case_id: str,
    contact_id: str,
    approval_code: str,
    decision: str,
) -> dict:
    if decision not in ("APPROVE", "REJECT"):
        return {"error": "Decision must be APPROVE or REJECT"}

    secret = _secret()
    case = get_task(case_id)

    if case is None or case.get("kind") != "scam_case":
        return {"error": "Case not found"}

    if case.get("status") != "AWAITING_FAMILY":
        return {"error": "Case already decided"}

    entry = _active_entry(case, contact_id)

    if entry is None:
        return {"error": "No active approval for this contact"}

    if not verify_token(
        secret,
        case_id,
        contact_id,
        entry["issued_at"],
        approval_code,
    ):
        outcome = _register_wrong_code(case_id, contact_id)

        if outcome is None:
            return {"error": "Case already decided"}

        record_event(
            case_id,
            "BAD_APPROVAL_CODE",
            {"contact_id": contact_id, "attempt": outcome["attempts"]},
        )

        if outcome["locked"]:
            return {"error": "Too many wrong codes. This contact is locked."}

        return {
            "error": "Invalid approval code",
            "attempts_left": max(0, MAX_WRONG_CODES - outcome["attempts"]),
        }

    approved = decision == "APPROVE"
    decided_at = _now_iso()

    updated = _conditional_update(
        case_id,
        "AWAITING_FAMILY",
        {
            "status": "APPROVED" if approved else "REJECTED",
            f"approvals.{contact_id}.used": True,
            "payment_status": "RELEASED" if approved else "BLOCKED",
            "approved": approved,
            "decided_by": contact_id,
            "decided_at": decided_at,
        },
        extra_condition="approvals.#cid.used = :false",
        extra_names={"#cid": contact_id},
        extra_values={":false": False},
    )

    if updated is None:
        return {"error": "Case already decided"}

    name = _contact_name(case, contact_id)

    record_event(
        case_id,
        "FAMILY_APPROVED" if approved else "FAMILY_REJECTED",
        {"contact_id": contact_id, "name": name},
    )
    record_event(
        case_id,
        "PAYMENT_RELEASED" if approved else "PAYMENT_BLOCKED",
        {"contact_id": contact_id},
    )

    return {
        "case_id": case_id,
        "status": updated.get("status"),
        "payment_status": updated.get("payment_status"),
        "decided_by": contact_id,
        "message": (
            "Payment approved and released."
            if approved
            else "Payment rejected. It stays blocked."
        ),
    }


# --------------------------------------------------------------------------
# Task 8: case receipt
# --------------------------------------------------------------------------


def get_case_receipt_logic(case_id: str, owner_id: str) -> dict:
    case = _owned_case(case_id, owner_id)

    if case is None:
        return {"error": "Case not found"}

    return build_case_receipt(case, get_task_events(case_id))