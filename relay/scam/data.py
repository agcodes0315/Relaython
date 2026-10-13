from __future__ import annotations

import copy

# Protection profiles, keyed by owner_id.
# payment_limit is in rupees: a payment above it to a NEW payee is held.
# contacts are the trusted family members, asked in 'order'.
DEMO_PROFILES: dict[str, dict] = {
    "user_savita": {
        "owner_id": "user_savita",
        "display_name": "Savita",
        "payment_limit": 10000,
        "cooling_off_minutes": 30,
        "contacts": [
            {"contact_id": "c_rohan", "name": "Rohan", "order": 1},
            {"contact_id": "c_anita", "name": "Anita", "order": 2},
        ],
    },
}

# Normalized 10-digit number -> reputation. All obviously fake (900000000x).
SYNTHETIC_NUMBERS: dict[str, dict] = {
    "9000000001": {"reputation": "KNOWN_SCAM", "reports": 47},
    "9000000002": {"reputation": "KNOWN_SCAM", "reports": 31},
    "9000000003": {"reputation": "SUSPICIOUS", "reports": 6},
    "9000000004": {"reputation": "SUSPICIOUS", "reports": 3},
    "9000000010": {"reputation": "TRUSTED", "reports": 0},
}


def get_profile(owner_id: str) -> dict | None:
    """Return a deep copy of the protection profile, or None if unknown.

    A copy is returned so callers can never change the demo data by accident.
    """
    if not isinstance(owner_id, str):
        return None

    profile = DEMO_PROFILES.get(owner_id)

    if profile is None:
        return None

    return copy.deepcopy(profile)