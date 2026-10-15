from __future__ import annotations

import copy
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from relay.decision_receipt import build_decision_receipt, receipt_event
from relay.scam.scoring import mask_digits

# Detail keys that must never reach a receipt. A key is dropped when its
# lower-cased name contains any of these words, at every depth.
_SECRET_WORDS = ("approval_code", "token", "secret")

_OUTCOMES = {
    "CLEARED": "Payment looked safe and was cleared.",
    "WARNED": "Payment was allowed with a warning.",
    "BLOCKED": "Payment was blocked.",
    "HELD": "Payment is on hold.",
    "AWAITING_FAMILY": "Payment is on hold, waiting for a family decision.",
    "APPROVED": "A family member approved and the payment was released.",
    "REJECTED": "A family member rejected the payment. It stayed blocked.",
    "EXPIRED_BLOCKED": (
        "Nobody answered before the hold expired. "
        "The payment stayed blocked."
    ),
}


# ---------------------------------------------------------------- cleaning


def _is_secret_key(key: Any) -> bool:
    lowered = str(key).lower()
    return any(word in lowered for word in _SECRET_WORDS)


def _clean(value: Any) -> Any:
    """Deep copy that drops secret keys and makes everything JSON-safe.

    Works at every depth (dicts inside lists inside dicts). The input is
    never modified.
    """
    if isinstance(value, dict):
        return {
            str(key): _clean(item)
            for key, item in value.items()
            if not _is_secret_key(key)
        }

    if isinstance(value, (list, tuple, set, frozenset)):
        return [_clean(item) for item in value]

    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


# --------------------------------------------------------------- summaries


def _text(value: Any, fallback: str = "unknown") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def _money(amount: Any) -> str:
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        return "an unknown amount"

    if float(amount).is_integer():
        return f"Rs {int(amount)}"

    return f"Rs {amount:.2f}"


def _summarize(event_type: str, details: dict) -> str:
    d = details if isinstance(details, dict) else {}

    if event_type == "CASE_OPENED":
        return (
            "Protection case opened with risk "
            f"{_text(d.get('risk_score'))} ({_text(d.get('risk_level'))})."
        )

    if event_type == "POLICY_EVALUATED":
        return f"Safety policy decided: {_text(d.get('decision'))}."

    if event_type == "PAYMENT_HELD":
        return (
            f"{_money(d.get('amount'))} to {_text(d.get('payee_label'))} "
            "was put on hold."
        )

    if event_type == "CONTACT_ALERTED":
        return f"Trusted contact {_text(d.get('name') or d.get('contact_id'))} was alerted."

    if event_type == "ESCALATED":
        return (
            "Escalated from "
            f"{_text(d.get('from_contact_id'))} to "
            f"{_text(d.get('to_contact_id'))} because there was no answer."
        )

    if event_type == "FAMILY_APPROVED":
        return (
            f"{_text(d.get('name') or d.get('contact_id'))} "
            "approved the payment with a valid code."
        )

    if event_type == "FAMILY_REJECTED":
        return (
            f"{_text(d.get('name') or d.get('contact_id'))} "
            "rejected the payment."
        )

    if event_type == "PAYMENT_RELEASED":
        return "The held payment was released."

    if event_type == "PAYMENT_BLOCKED":
        return "The payment was blocked and no money moved."

    if event_type == "HOLD_EXPIRED":
        return "The hold expired with no family decision."

    if event_type == "BAD_APPROVAL_CODE":
        return (
            f"A wrong approval code was tried for {_text(d.get('contact_id'))} "
            f"(attempt {_text(d.get('attempt'))})."
        )

    if event_type == "RESUME_TRIGGERED":
        return "The cooling-off timer woke the case up."

    if event_type == "WAIT_SCHEDULED":
        return "A timer was scheduled for this case."

    return f"Event recorded: {_text(event_type, 'unknown event')}."


# ----------------------------------------------------------------- answers


def _contact_name(case: dict, contact_id: Any) -> str:
    for contact in case.get("contacts") or []:
        if isinstance(contact, dict) and contact.get("contact_id") == contact_id:
            return _text(contact.get("name"), _text(contact_id))
    return _text(contact_id)


def _who_was_alerted(case: dict, events: list[dict]) -> list[dict]:
    alerted: list[dict] = []

    for event in events:
        details = event.get("details") or {}
        kind = event.get("event_type")

        if kind == "CONTACT_ALERTED":
            contact_id = details.get("contact_id")
            alerted.append(
                {
                    "contact_id": contact_id,
                    "name": details.get("name") or _contact_name(case, contact_id),
                    "at": event.get("timestamp"),
                    "how": "first alert",
                }
            )

        elif kind == "ESCALATED":
            contact_id = details.get("to_contact_id")
            alerted.append(
                {
                    "contact_id": contact_id,
                    "name": _contact_name(case, contact_id),
                    "at": event.get("timestamp"),
                    "how": "escalation",
                }
            )

    return alerted


def _who_decided(case: dict, events: list[dict]) -> str:
    for event in events:
        kind = event.get("event_type")

        if kind in ("FAMILY_APPROVED", "FAMILY_REJECTED"):
            details = event.get("details") or {}
            contact_id = details.get("contact_id") or case.get("decided_by")
            verb = "APPROVE" if kind == "FAMILY_APPROVED" else "REJECT"
            return (
                f"{_text(contact_id)} decided {verb} with a valid approval "
                f"code at {_text(event.get('timestamp'))}."
            )

    if case.get("status") == "EXPIRED_BLOCKED" or any(
        event.get("event_type") == "HOLD_EXPIRED" for event in events
    ):
        return "nobody answered"

    return "No decision yet."


def _what_was_held(case: dict) -> str:
    if case.get("payment_status") == "NONE":
        return "Nothing was held."

    return (
        f"{_money(case.get('amount'))} to "
        f"{mask_digits(_text(case.get('payee_label'), 'unknown payee'))}"
        f" (payment status: {_text(case.get('payment_status'))})."
    )


def _how_escalation_happened(events: list[dict]) -> str:
    lines = []

    for event in events:
        if event.get("event_type") == "ESCALATED":
            details = event.get("details") or {}
            lines.append(
                f"At {_text(event.get('timestamp'))} the case moved from "
                f"{_text(details.get('from_contact_id'))} to "
                f"{_text(details.get('to_contact_id'))}."
            )

    return " ".join(lines) if lines else "No escalation was needed."


def _final_outcome(case: dict) -> str:
    return _OUTCOMES.get(
        str(case.get("status")),
        f"Current status: {_text(case.get('status'))}.",
    )


def _complaint_summary(
    case: dict,
    alerted: list[dict],
    outcome: str,
) -> str:
    payee = mask_digits(_text(case.get("payee_label"), "unknown payee"))

    if alerted:
        parts = [
            f"{_text(item.get('name'))} at {_text(item.get('at'))}"
            for item in alerted
        ]
        family_line = "Family alerted (UTC): " + "; ".join(parts) + "."
    else:
        family_line = "Family alerted: no alert was recorded."

    lines = [
        f"Relay Shield case {_text(case.get('task_id') or case.get('case_id'))}",
        (
            f"Opened (UTC): {_text(case.get('created_at'))}. "
            f"Risk score {_text(case.get('risk_score'))} "
            f"({_text(case.get('risk_level'))})."
        ),
        f"Payment: {_money(case.get('amount'))} to {payee} (masked payee).",
        family_line,
        f"Outcome: {outcome}",
    ]

    if case.get("decided_at"):
        lines.append(f"Final decision time (UTC): {case['decided_at']}")

    return "\n".join(lines)


# ------------------------------------------------------------------ public


def build_case_receipt(case: dict, events: list[dict]) -> dict:
    """Turn a case and its audit events into a readable evidence trail.

    Pure: no AWS, and neither input is modified. Approval codes and other
    secrets are removed at every depth. The result is plain JSON-safe data.
    """
    case = _clean(case if isinstance(case, dict) else {})
    fallback_time = case.get("created_at")

    items: list[dict] = []
    cleaned_events: list[dict] = []

    for raw in events or []:
        if not isinstance(raw, dict):
            continue

        event_type = _text(raw.get("event_type"), "UNKNOWN")
        details = _clean(raw.get("details") or {})

        if not isinstance(details, dict):
            details = {}

        timestamp = raw.get("timestamp") or fallback_time

        items.append(
            receipt_event(
                event_type,
                _summarize(event_type, details),
                details=details,
                timestamp=_clean(timestamp) if timestamp else None,
            )
        )

        cleaned_events.append(
            {
                "event_type": event_type,
                "timestamp": _clean(timestamp) if timestamp else "",
                "details": details,
            }
        )

    receipt = build_decision_receipt(items)

    # Same stable sort build_decision_receipt uses, so the answers below
    # read the events in the same order the person sees them.
    cleaned_events.sort(key=lambda item: item.get("timestamp", ""))

    alerted = _who_was_alerted(case, cleaned_events)
    outcome = _final_outcome(case)

    receipt["case"] = {
        "case_id": case.get("task_id") or case.get("case_id"),
        "status": case.get("status"),
        "payment_status": case.get("payment_status"),
        "risk_score": case.get("risk_score"),
        "risk_level": case.get("risk_level"),
        "amount": case.get("amount"),
        "payee_label": mask_digits(_text(case.get("payee_label"), "")),
    }

    receipt["answers"] = {
        "why_it_was_flagged": list(case.get("signals") or []),
        "what_was_held": _what_was_held(case),
        "who_was_alerted_and_when": alerted,
        "who_decided_and_how": _who_decided(case, cleaned_events),
        "how_escalation_happened": _how_escalation_happened(cleaned_events),
        "final_outcome": outcome,
    }

    receipt["complaint_summary"] = _complaint_summary(case, alerted, outcome)

    # Belt and braces: whatever happens above, never let a secret key out.
    return copy.deepcopy(_clean(receipt))