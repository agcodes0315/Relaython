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