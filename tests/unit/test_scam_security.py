from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import relay.scam.service as service
import server


def test_invalid_owner_ids_are_rejected():
    invalid = [
        "",
        " ",
        "../admin",
        "user/other",
        "user@evil",
        "a" * 65,
    ]

    for owner_id in invalid:
        assert service._valid_owner_id(owner_id) is False


def test_safe_owner_ids_are_accepted():
    for owner_id in (
        "user_savita",
        "user-123",
        "USER_ABC",
        "abc123",
    ):
        assert service._valid_owner_id(owner_id) is True


@pytest.mark.parametrize(
    "amount",
    [
        -1,
        -0.01,
        10_000_000.01,
        99_999_999,
        True,
        "not-a-number",
    ],
)
def test_unsafe_amounts_are_rejected(amount):
    assert service._valid_amount(amount) is False


@pytest.mark.parametrize(
    "amount",
    [
        None,
        0,
        1,
        25_000,
        10_000_000,
    ],
)
def test_supported_amounts_are_accepted(amount):
    assert service._valid_amount(amount) is True


def test_open_case_rejects_invalid_owner_before_profile_lookup(monkeypatch):
    called = False

    def fake_profile(_owner_id):
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(service, "get_profile", fake_profile)

    result = service.open_protection_case_logic(
        "../admin",
        85,
        25_000,
        "Test payee",
        True,
    )

    assert result == {"error": "Invalid owner_id"}
    assert called is False


def test_open_case_rejects_out_of_range_amount_before_profile_lookup(monkeypatch):
    called = False

    def fake_profile(_owner_id):
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(service, "get_profile", fake_profile)

    result = service.open_protection_case_logic(
        "user_savita",
        85,
        10_000_001,
        "Test payee",
        True,
    )

    assert result == {
        "error": "Amount must be between 0 and 10000000"
    }
    assert called is False


def test_wrong_owner_matches_missing_case(monkeypatch):
    stored_case = {
        "task_id": "case-security-test",
        "kind": "scam_case",
        "owner_id": "user_savita",
        "status": "AWAITING_FAMILY",
    }

    monkeypatch.setattr(
        service,
        "get_task",
        lambda case_id: (
            stored_case
            if case_id == "case-security-test"
            else None
        ),
    )

    wrong_owner = service.get_protection_case_logic(
        "case-security-test",
        "user_other",
    )
    missing_case = service.get_protection_case_logic(
        "case-does-not-exist",
        "user_savita",
    )

    assert wrong_owner == {"error": "Case not found"}
    assert missing_case == {"error": "Case not found"}
    assert wrong_owner == missing_case


def test_receipt_wrong_owner_does_not_read_audit(monkeypatch):
    stored_case = {
        "task_id": "case-security-test",
        "kind": "scam_case",
        "owner_id": "user_savita",
        "status": "AWAITING_FAMILY",
    }

    monkeypatch.setattr(
        service,
        "get_task",
        lambda _case_id: stored_case,
    )

    def fail_if_called(_case_id):
        raise AssertionError(
            "audit must not be read for the wrong owner"
        )

    monkeypatch.setattr(
        service,
        "get_task_events",
        fail_if_called,
    )

    result = service.get_case_receipt_logic(
        "case-security-test",
        "user_other",
    )

    assert result == {"error": "Case not found"}


def test_missing_shield_secret_fails_closed(monkeypatch):
    monkeypatch.delenv(
        "RELAY_SHIELD_SECRET",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="RELAY_SHIELD_SECRET is not set",
    ):
        service._secret()


def test_message_over_2000_characters_is_rejected(monkeypatch):
    called = False

    def fake_analyze(_text, _sender=None):
        nonlocal called
        called = True
        return {"risk_score": 0}

    monkeypatch.setattr(
        server,
        "analyze_message_logic",
        fake_analyze,
    )

    result = server.analyze_message(
        "x" * 2001,
        None,
    )

    assert result == {
        "error": "Message text must be 2000 characters or fewer"
    }
    assert called is False


def test_message_at_2000_characters_is_allowed(monkeypatch):
    monkeypatch.setattr(
        server,
        "analyze_message_logic",
        lambda text, sender=None: {
            "risk_score": 0,
            "length": len(text),
        },
    )

    result = server.analyze_message(
        "x" * 2000,
        None,
    )

    assert result["length"] == 2000


def test_family_code_only_exists_in_inbox_surface():
    inbox_source = inspect.getsource(
        service.get_family_inbox_logic
    )
    alert_source = inspect.getsource(
        service.alert_trusted_contact_logic
    )
    case_source = inspect.getsource(
        service.get_protection_case_logic
    )
    receipt_source = inspect.getsource(
        service.get_case_receipt_logic
    )

    assert '"approval_code": code' in inbox_source

    assert '"approval_code": code' not in alert_source
    assert '"approval_code": code' not in case_source
    assert '"approval_code": code' not in receipt_source


def test_wrong_code_limit_is_three():
    assert service.MAX_WRONG_CODES == 3


def test_alert_limit_is_five():
    assert service.MAX_ALERT_CALLS == 5


def test_amount_limit_is_ten_million():
    assert service.MAX_PAYMENT_AMOUNT == 10_000_000


def test_security_sensitive_mutations_use_conditional_updates():
    source = Path("relay/scam/service.py").read_text(
        encoding="utf-8"
    )

    assert "def record_family_decision_logic(" in source
    assert "def alert_trusted_contact_logic(" in source

    decision_start = source.index(
        "def record_family_decision_logic("
    )
    receipt_start = source.index(
        "def get_case_receipt_logic("
    )

    alert_start = source.index(
        "def alert_trusted_contact_logic("
    )
    inbox_start = source.index(
        "def get_family_inbox_logic("
    )

    decision_source = source[
        decision_start:receipt_start
    ]
    alert_source = source[
        alert_start:inbox_start
    ]

    assert "_conditional_update(" in decision_source
    assert "_conditional_update(" in alert_source

    # Whole-record persistence is allowed only for initial case creation.
    assert source.count("save_task(case)") == 1
