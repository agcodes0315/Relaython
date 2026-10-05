from enum import Enum


class RiskLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    REVERSIBLE = "REVERSIBLE"
    COMMITMENT = "COMMITMENT"
    SPEND = "SPEND"
    IRREVERSIBLE = "IRREVERSIBLE"


def provider_is_within_budget(provider: dict, budget: float) -> bool:
    return provider["price"] <= budget


def provider_day_is_allowed(provider: dict, excluded_days: list[str]) -> bool:
    return provider["available_day"] not in excluded_days


def provider_is_valid(
    provider: dict,
    budget: float,
    excluded_days: list[str],
) -> bool:
    return (
        provider_is_within_budget(provider, budget)
        and provider_day_is_allowed(provider, excluded_days)
    )


def evaluate_action(
    action: str,
    amount: float | None = None,
    max_budget: float | None = None,
) -> dict:
    """
    Decide whether an action is automatically allowed,
    requires human approval, or must be blocked.
    """

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
            "reason": "Selecting a provider does not create a booking.",
        }

    if action == "BOOK_PROVIDER":
        if amount is None:
            return {
                "decision": "BLOCK",
                "risk": RiskLevel.SPEND.value,
                "reason": "Booking amount is missing.",
            }

        if max_budget is not None and amount > max_budget:
            return {
                "decision": "BLOCK",
                "risk": RiskLevel.SPEND.value,
                "reason": "Booking exceeds the user's maximum budget.",
            }

        return {
            "decision": "REQUIRE_APPROVAL",
            "risk": RiskLevel.SPEND.value,
            "reason": "Booking involves spending money.",
        }

    return {
        "decision": "BLOCK",
        "risk": RiskLevel.IRREVERSIBLE.value,
        "reason": "Unknown action is blocked by default.",
    }