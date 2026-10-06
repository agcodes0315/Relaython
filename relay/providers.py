from datetime import date


PROVIDERS = [
    {
        "provider_id": "provider_1",
        "name": "CoolCare",
        "price": 1450,
        "available_date": "2026-10-09",
        "is_available": True,
    },
    {
        "provider_id": "provider_2",
        "name": "QuickFix",
        "price": 1800,
        "available_date": "2026-10-07",
        "is_available": True,
    },
    {
        "provider_id": "provider_3",
        "name": "PremiumAir",
        "price": 2600,
        "available_date": "2026-10-06",
        "is_available": True,
    },
]


def _enrich_provider(provider: dict) -> dict:
    enriched = provider.copy()

    available_date = enriched.get("available_date")

    if available_date:
        parsed_date = date.fromisoformat(
            available_date
        )

        enriched["available_day"] = (
            parsed_date.strftime("%A")
        )

    return enriched


def get_providers() -> list[dict]:
    return [
        _enrich_provider(provider)
        for provider in PROVIDERS
    ]


def get_provider(
    provider_id: str,
) -> dict | None:
    for provider in PROVIDERS:
        if provider["provider_id"] == provider_id:
            return _enrich_provider(provider)

    return None


def set_provider_availability(
    provider_id: str,
    is_available: bool,
) -> bool:
    for provider in PROVIDERS:
        if provider["provider_id"] == provider_id:
            provider["is_available"] = is_available
            return True

    return False


def mark_provider_unavailable(
    provider_id: str,
) -> bool:
    return set_provider_availability(
        provider_id,
        False,
    )


def restore_provider(
    provider_id: str,
) -> bool:
    return set_provider_availability(
        provider_id,
        True,
    )