from datetime import date


PROVIDERS = [
    {
        "provider_id": "provider_1",
        "name": "CoolCare",
        "price": 1450,
        "available_date": "2026-10-09",
    },
    {
        "provider_id": "provider_2",
        "name": "QuickFix",
        "price": 1800,
        "available_date": "2026-10-07",
    },
    {
        "provider_id": "provider_3",
        "name": "PremiumAir",
        "price": 2600,
        "available_date": "2026-10-06",
    },
]


def enrich_provider(provider: dict) -> dict:
    """
    Return provider data with a weekday derived
    deterministically from available_date.
    """

    provider_date = date.fromisoformat(
        provider["available_date"]
    )

    return {
        **provider,
        "available_day": provider_date.strftime("%A"),
    }


def get_providers() -> list[dict]:
    return [
        enrich_provider(provider)
        for provider in PROVIDERS
    ]
