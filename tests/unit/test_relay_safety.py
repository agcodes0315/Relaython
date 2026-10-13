from relay.policy import (
    provider_is_valid,
    validate_transition,
)


def test_provider_within_all_constraints():
    provider = {
        "provider_id": "p1",
        "name": "Test",
        "price": 1500,
        "available_date": "2026-10-09",
    }

    assert provider_is_valid(
        provider=provider,
        budget=2000,
        excluded_days=["Thursday"],
        deadline="2026-10-10",
    )


def test_over_budget_provider_rejected():
    provider = {
        "provider_id": "p1",
        "name": "Test",
        "price": 2500,
        "available_date": "2026-10-09",
    }

    assert not provider_is_valid(
        provider=provider,
        budget=2000,
        excluded_days=[],
        deadline="2026-10-10",
    )


def test_provider_after_deadline_rejected():
    provider = {
        "provider_id": "p1",
        "name": "Test",
        "price": 1500,
        "available_date": "2026-10-12",
    }

    assert not provider_is_valid(
        provider=provider,
        budget=2000,
        excluded_days=[],
        deadline="2026-10-10",
    )


def test_excluded_weekday_rejected():
    provider = {
        "provider_id": "p1",
        "name": "Test",
        "price": 1500,
        "available_date": "2026-10-08",
    }

    assert not provider_is_valid(
        provider=provider,
        budget=2000,
        excluded_days=["Thursday"],
        deadline="2026-10-10",
    )


def test_valid_state_transition():
    valid, _ = validate_transition(
        "CREATED",
        "PROVIDERS_FOUND",
    )

    assert valid


def test_invalid_state_transition():
    valid, _ = validate_transition(
        "CREATED",
        "APPROVED",
    )

    assert not valid
