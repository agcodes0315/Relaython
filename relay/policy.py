from datetime import date
from enum import Enum


class RiskLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    REVERSIBLE = "REVERSIBLE"
    COMMITMENT = "COMMITMENT"
    SPEND = "SPEND"
    IRREVERSIBLE = "IRREVERSIBLE"


ALLOWED_TRANSITIONS = {
    "CREATED": {
        "PROVIDERS_FOUND",
        "NO_PROVIDERS",
        "BLOCKED",
    },
    "PROVIDERS_FOUND": {
        "AWAITING_DECISION",
        "BLOCKED",
    },
    "AWAITING_DECISION": {
        "NEEDS_APPROVAL",
        "BLOCKED",
    },
    "NEEDS_APPROVAL": {
        "APPROVED",
        "REJECTED",
        "BLOCKED",
    },
    "NO_PROVIDERS": set(),
    "APPROVED": set(),
    "REJECTED": set(),
    "BLOCKED": set(),
}


def validate_transition(
    current_status: str,
    next_status: str,
) -> tuple[bool, str]:
    allowed = ALLOWED_TRANSITIONS.get(
        current_status,
        set(),
    )

    if next_status in allowed:
        return True, "Transition allowed."

    return (
        False,
        (
            f"Invalid state transition: "
            f"{current_status} -> {next_status}"
        ),
    )


def provider_is_within_budget(
    provider: dict,
    budget: float,
) -> bool:
    return provider["price"] <= budget


def provider_date_is_before_deadline(
    provider: dict,
    deadline: str,
) -> bool:
    provider_date = date.fromisoformat(
        provider["available_date"]
    )

    deadline_date = date.fromisoformat(
        deadline
    )

    return provider_date <= deadline_date


def provider_day_is_allowed(
    provider: dict,
    excluded_days: list[str],
) -> bool:
    provider_date = date.fromisoformat(
        provider["available_date"]
    )

    weekday = provider_date.strftime("%A")

    normalized_excluded = {
        day.strip().lower()
        for day in excluded_days
    }

    return weekday.lower() not in normalized_excluded


def provider_is_valid(
    provider: dict,
    budget: float,
    excluded_days: list[str],
    deadline: str,
) -> bool:
    return (
        provider_is_within_budget(
            provider,
            budget,
        )
        and provider_day_is_allowed(
            provider,
            excluded_days,
        )
        and provider_date_is_before_deadline(
            provider,
            deadline,
        )
    )


def evaluate_action(
    action: str,
    amount: float | None = None,
    max_budget: float | None = None,
) -> dict:
    if action == "SEARCH_PROVIDERS":
        return {
            "decision": "ALLOW",
            "risk": RiskLevel.READ_ONLY.value,
            "reason": "Searching providers is read-only.",
        }

    if action == "SELECT_PROVIDER":
        return {
            "decision": "ALLOW",
            "risk": RiskLevel.REVERSIBLE.value,
            "reason": (
                "Selecting a provider does not create "
                "a booking."
            ),
        }

    if action == "BOOK_PROVIDER":
        if amount is None:
            return {
                "decision": "BLOCK",
                "risk": RiskLevel.SPEND.value,
                "reason": "Booking amount is missing.",
            }

        if (
            max_budget is not None
            and amount > max_budget
        ):
            return {
                "decision": "BLOCK",
                "risk": RiskLevel.SPEND.value,
                "reason": (
                    "Booking exceeds the user's "
                    "maximum budget."
                ),
            }

        return {
            "decision": "REQUIRE_APPROVAL",
            "risk": RiskLevel.SPEND.value,
            "reason": (
                "Booking involves spending money."
            ),
        }

    return {
        "decision": "BLOCK",
        "risk": RiskLevel.IRREVERSIBLE.value,
        "reason": (
            "Unknown action is blocked by default."
        ),
    }
