from __future__ import annotations
from datetime import datetime
import relay.scam.service as service
def install_fakes(monkeypatch):
    saved = {}
    events = []
    def fake_save(task):
        saved[task["task_id"]] = dict(
            task
        )

        return task
    def fake_get(task_id):
        task = saved.get(task_id)

        return (
            dict(task)
            if task is not None
            else None
        )
    def fake_event(
        task_id,
        event_type,
        details,
    ):
        events.append(
            {
                "task_id": task_id,
                "event_type": event_type,
                "details": details,
            }
        )

    monkeypatch.setattr(
        service,
        "save_task",
        fake_save,
    )

    monkeypatch.setattr(
        service,
        "get_task",
        fake_get,
    )

    monkeypatch.setattr(
        service,
        "record_event",
        fake_event,
    )

    return saved, events


def test_hold_case(
    monkeypatch,
):
    saved, events = install_fakes(
        monkeypatch
    )

    case = (
        service
        .open_protection_case_logic(
            owner_id="user_savita",
            risk_score=85,
            amount=25000,
            payee_label=(
                "Payee 9876543210"
            ),
            payee_is_new=True,
            signals=[
                "otp_request",
                "impersonation",
            ],
        )
    )

    assert case["kind"] == (
        "scam_case"
    )

    assert case["task_id"].startswith(
        "case-"
    )

    assert case["status"] == "HELD"
    assert (
        case["payment_status"]
        == "HELD"
    )

    assert case["approvals"] == {}

    assert (
        "hold_started_at"
        in case
    )

    assert (
        "hold_expires_at"
        in case
    )

    assert (
        case["task_id"]
        in saved
    )

    assert [
        event["event_type"]
        for event in events
    ] == [
        "CASE_OPENED",
        "POLICY_EVALUATED",
        "PAYMENT_HELD",
    ]


def test_allow_case_is_cleared(
    monkeypatch,
):
    install_fakes(monkeypatch)

    case = (
        service
        .open_protection_case_logic(
            "user_savita",
            10,
            500,
            "Known payee",
            False,
        )
    )

    assert case["status"] == (
        "CLEARED"
    )

    assert (
        case["payment_status"]
        == "NONE"
    )
def test_warn_case(
    monkeypatch,
):
    install_fakes(monkeypatch)

    case = (
        service
        .open_protection_case_logic(
            "user_savita",
            45,
            500,
            "Payee",
            False,
        )
    )

    assert case["status"] == (
        "WARNED"
    )


def test_invalid_score_blocks(
    monkeypatch,
):
    install_fakes(monkeypatch)

    case = (
        service
        .open_protection_case_logic(
            "user_savita",
            150,
            500,
            "Payee",
            True,
        )
    )

    assert case["status"] == (
        "BLOCKED"
    )

    assert (
        case["payment_status"]
        == "BLOCKED"
    )
def test_unknown_owner_errors(
    monkeypatch,
):
    saved, _ = install_fakes(
        monkeypatch
    )
    result = (
        service
        .open_protection_case_logic(
            "unknown-user",
            85,
            25000,
            "Payee",
            True,
        )
    )
    assert result == {
        "error":
        "Unknown protected user"
    }

    assert saved == {}


def test_payee_is_masked(
    monkeypatch,
):
    install_fakes(monkeypatch)

    case = (
        service
        .open_protection_case_logic(
            "user_savita",
            85,
            25000,
            "Payee 9876543210",
            True,
        )
    )

    assert (
        "9876543210"
        not in case["payee_label"]
    )


def test_cooling_period_clamps(
    monkeypatch,
):
    install_fakes(monkeypatch)

    low = (
        service
        .open_protection_case_logic(
            "user_savita",
            85,
            25000,
            "Payee",
            True,
            cooling_off_minutes=1,
        )
    )
    high = (
        service
        .open_protection_case_logic(
            "user_savita",
            85,
            25000,
            "Payee",
            True,
            cooling_off_minutes=500,
        )
    )

    assert (
        low[
            "cooling_off_minutes"
        ]
        == 2
    )

    assert (
        high[
            "cooling_off_minutes"
        ]
        == 60
    )


def test_hold_expiry_matches_cooling_period(
    monkeypatch,
):
    install_fakes(monkeypatch)

    case = (
        service
        .open_protection_case_logic(
            "user_savita",
            85,
            25000,
            "Payee",
            True,
            cooling_off_minutes=30,
        )
    )

    start = datetime.fromisoformat(
        case["hold_started_at"]
    )

    expiry = datetime.fromisoformat(
        case["hold_expires_at"]
    )

    assert (
        expiry - start
    ).total_seconds() == 1800


def test_wrong_owner_and_missing_case_are_identical(
    monkeypatch,
):
    saved, _ = install_fakes(
        monkeypatch
    )

    case = (
        service
        .open_protection_case_logic(
            "user_savita",
            10,
            500,
            "Payee",
            False,
        )
    )

    missing = (
        service
        .get_protection_case_logic(
            "case-does-not-exist",
            "attacker",
        )
    )

    wrong_owner = (
        service
        .get_protection_case_logic(
            case["task_id"],
            "attacker",
        )
    )

    assert missing == wrong_owner

    assert missing == {
        "error": "Case not found"
    }


def test_correct_owner_can_read_case(
    monkeypatch,
):
    install_fakes(monkeypatch)

    case = (
        service
        .open_protection_case_logic(
            "user_savita",
            10,
            500,
            "Payee",
            False,
        )
    )
    loaded = (
        service
        .get_protection_case_logic(
            case["task_id"],
            "user_savita",
        )
    )
    assert loaded["task_id"] == (
        case["task_id"]
    )