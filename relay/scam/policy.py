

from __future__ import annotations

import math

from relay.policy import RiskLevel

# Escalation to the next family contact is an EVENT inside AWAITING_FAMILY,
# not a separate state.
CASE_TRANSITIONS: dict[str, set[str]] = {
    "OPENED": {"CLEARED", "WARNED", "HELD", "BLOCKED"},
    "WARNED": {"HELD", "CLEARED"},
    "HELD": {"AWAITING_FAMILY", "BLOCKED"},
    "AWAITING_FAMILY": {"APPROVED", "REJECTED", "EXPIRED_BLOCKED"},
    "CLEARED": set(),
    "BLOCKED": set(),
    "APPROVED": set(),
    "REJECTED": set(),
    "EXPIRED_BLOCKED": set(),
}

FINAL_STATES = frozenset(
    state for state, exits in CASE_TRANSITIONS.items() if not exits
)


def is_final_state(status: str) -> bool:
    """True when a case in this status can never change again."""
    return status in FINAL_STATES


def validate_case_transition(
    current_status: str,
    next_status: str,
) -> tuple[bool, str]:
    if not isinstance(current_status, str) or not isinstance(next_status, str):
        return (
            False,
            f"Invalid case transition: {current_status} -> {next_status}",
        )

    allowed = CASE_TRANSITIONS.get(current_status, set())

    if next_status in allowed:
        return True, "Transition allowed."

    return (
        False,
        f"Invalid case transition: {current_status} -> {next_status}",
    )


def _is_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _blocked(reason: str) -> dict:
    return {
        "decision": "BLOCK",
        "risk": RiskLevel.IRREVERSIBLE.value,
        "reasons": [reason],
    }


def assess_payment(
    risk_score: int,
    amount: float | None,
    payee_is_new: bool,
    profile: dict,
) -> dict:
    """Decide what to do with a payment: ALLOW, WARN, HOLD or BLOCK.

    Rules, in this order:
      1. Invalid input                               -> BLOCK
      2. risk >= 70 and a payment amount above zero  -> HOLD
      3. amount over the limit and a new payee       -> HOLD
      4. risk >= 40                                  -> WARN
      5. otherwise                                   -> ALLOW
    """
    # 1. Invalid input is blocked (default-deny).
    if not _is_number(risk_score) or not 0 <= risk_score <= 100:
        return _blocked("Risk score is missing or outside 0 to 100.")

    if amount is not None and (not _is_number(amount) or amount < 0):
        return _blocked("Payment amount is invalid.")

    if not isinstance(profile, dict) or not _is_number(profile.get("payment_limit")):
        return _blocked("Protection profile has no valid payment limit.")

    limit = profile["payment_limit"]
    has_payment = amount is not None and amount > 0
    over_limit = has_payment and amount > limit
    new_payee = bool(payee_is_new)

    # 2. High scam risk while money is moving.
    if risk_score >= 70 and has_payment:
        reasons = [
            f"Scam risk is high (score {int(risk_score)}) "
            f"and a payment of Rs {amount:g} is being made."
        ]

        if over_limit and new_payee:
            reasons.append(
                f"The amount is above the Rs {limit:g} limit and the payee is new."
            )

        return {
            "decision": "HOLD",
            "risk": RiskLevel.SPEND.value,
            "reasons": reasons,
        }

    # 3. Large payment to someone new.
    if over_limit and new_payee:
        return {
            "decision": "HOLD",
            "risk": RiskLevel.SPEND.value,
            "reasons": [
                f"The amount (Rs {amount:g}) is above the Rs {limit:g} limit "
                "and the payee is new."
            ],
        }

    # 4. Suspicious, but nothing to hold.
    if risk_score >= 40:
        if risk_score >= 70:
            reason = "Scam risk is high, but no payment is being made right now."
        else:
            reason = f"Scam risk is raised (score {int(risk_score)}). Be careful."

        return {
            "decision": "WARN",
            "risk": RiskLevel.REVERSIBLE.value,
            "reasons": [reason],
        }

    # 5. Looks fine.
    return {
        "decision": "ALLOW",
        "risk": RiskLevel.READ_ONLY.value,
        "reasons": ["Low scam risk and the payment is within the allowed limit."],
    }


def evaluate_scam_action(action: str) -> dict:
    """Risk tier and decision for each action Relay Shield can take.

    Names are matched exactly. Anything else is blocked by default.
    """
    if action == "ANALYZE_MESSAGE":
        return {
            "decision": "ALLOW",
            "risk": RiskLevel.READ_ONLY.value,
            "reason": "Analyzing a message is read-only.",
        }

    if action == "CHECK_NUMBER":
        return {
            "decision": "ALLOW",
            "risk": RiskLevel.READ_ONLY.value,
            "reason": "Checking a number is read-only.",
        }

    if action == "OPEN_CASE":
        return {
            "decision": "ALLOW",
            "risk": RiskLevel.REVERSIBLE.value,
            "reason": "Opening a protection case holds a payment but can be undone.",
        }

    if action == "ALERT_CONTACT":
        return {
            "decision": "ALLOW",
            "risk": RiskLevel.REVERSIBLE.value,
            "reason": "Alerting a trusted contact can be undone.",
        }

    if action == "FAMILY_DECISION":
        return {
            "decision": "REQUIRE_APPROVAL",
            "risk": RiskLevel.COMMITMENT.value,
            "reason": "Needs a valid family approval code.",
        }

    if action == "RELEASE_PAYMENT":
        return {
            "decision": "REQUIRE_APPROVAL",
            "risk": RiskLevel.IRREVERSIBLE.value,
            "reason": "Releasing a held payment cannot be undone and needs family approval.",
        }

    return {
        "decision": "BLOCK",
        "risk": RiskLevel.IRREVERSIBLE.value,
        "reason": "Unknown action is blocked by default.",
    }


def contact_at(profile: dict, index: int) -> dict | None:
    """The trusted contact at this position, ordered by their 'order' field.

    Returns a copy, or None when the index is out of range.
    """
    if not isinstance(profile, dict):
        return None

    contacts = profile.get("contacts")

    if not isinstance(contacts, list):
        return None

    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        return None

    ordered = sorted(
        (c for c in contacts if isinstance(c, dict)),
        key=lambda c: c.get("order", 10**9),
    )

    if index >= len(ordered):
        return None

    return dict(ordered[index])