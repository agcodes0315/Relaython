
from __future__ import annotations

import pytest

import relay.scam.service as service


@pytest.fixture(autouse=True)
def _no_real_alert_in_case_opening_tests(request, monkeypatch):
    """Opening a HOLD case now alerts the first contact, which needs
    DynamoDB and EventBridge. The older Task 5 tests only care about case
    opening, so they get a stub. Tests whose module name contains 'family'
    exercise the real alert logic and are left untouched."""
    if "family" in request.module.__name__:
        return

    monkeypatch.setattr(
        service,
        "alert_trusted_contact_logic",
        lambda case_id, owner_id: {
            "status": "HELD",
            "alerted_contact": {"contact_id": "c_rohan", "name": "Rohan"},
        },
    )