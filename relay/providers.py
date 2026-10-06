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


def get_providers() -> list[dict]:
    return [
        provider.copy()
        for provider in PROVIDERS
    ]


def mark_provider_unavailable(
    provider_id: str,
) -> dict | None:
    for provider in PROVIDERS:
        if provider["provider_id"] == provider_id:
            provider["is_available"] = False
            return provider.copy()

    return None


def mark_provider_available(
    provider_id: str,
) -> dict | None:
    for provider in PROVIDERS:
        if provider["provider_id"] == provider_id:
            provider["is_available"] = True
            return provider.copy()

    return None
