
from __future__ import annotations

import json
from decimal import Decimal

import pytest

import relay.scam.service as service
from scam_fakes import install

OWNER = "user_savita"


def open_hold(monkeypatch, store=None, minutes=2):
    store = store or install(monkeypatch)
    result = service.open_protection_case_logic(
        OWNER, 85, 25000.0, "UPI 9876543210", True, ["otp_request"], minutes
    )
    return store, result["task_id"], result


def inbox_code(case_id, contact_id="c_rohan"):
    return service.get_family_inbox_logic(case_id, contact_id)["approval_code"]


def test_opening_a_hold_case_alerts_the_first_contact(monkeypatch):
    store, case_id, result = open_hold(monkeypatch)

    assert result["alerted_contact"] == {"contact_id": "c_rohan", "name": "Rohan"}
    assert store.cases[case_id]["status"] == "AWAITING_FAMILY"
    assert store.cases[case_id]["current_contact_index"] == 0
    assert "CONTACT_ALERTED" in store.event_types(case_id)


def test_opening_a_hold_case_creates_escalation_and_expiry_timers(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)

    suffixes = [t["name_suffix"] for t in store.timers]
    assert suffixes == ["e1", "exp"]
    assert store.timers[0]["extra_payload"] == {"step": "ESCALATE", "to_index": 1}
    assert store.timers[1]["extra_payload"] == {"step": "EXPIRE"}
    assert all(t["persist_task"] is False for t in store.timers)
    assert store.timers[1]["run_at"].isoformat() == store.cases[case_id]["hold_expires_at"]


def test_second_alert_issues_no_new_code(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)
    before_events = store.event_types(case_id).count("CONTACT_ALERTED")
    before_timers = len(store.timers)

    again = service.alert_trusted_contact_logic(case_id, OWNER)

    assert again == {"already_alerted": True, "status": "AWAITING_FAMILY"}
    assert store.event_types(case_id).count("CONTACT_ALERTED") == before_events
    assert len(store.timers) == before_timers


def test_alert_with_wrong_owner_is_case_not_found(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)

    assert service.alert_trusted_contact_logic(case_id, "someone_else") == {
        "error": "Case not found"
    }


def test_alert_on_a_cleared_case_is_refused(monkeypatch):
    store = install(monkeypatch)
    result = service.open_protection_case_logic(OWNER, 5, 100.0, "Milk shop", False)

    outcome = service.alert_trusted_contact_logic(result["task_id"], OWNER)

    assert "error" in outcome
    assert store.timers == []


def test_correct_code_approves_and_releases(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)

    outcome = service.record_family_decision_logic(
        case_id, "c_rohan", inbox_code(case_id), "APPROVE"
    )

    case = store.cases[case_id]
    assert outcome["status"] == "APPROVED"
    assert case["status"] == "APPROVED"
    assert case["payment_status"] == "RELEASED"
    assert case["approved"] is True
    assert case["decided_by"] == "c_rohan"
    assert {"FAMILY_APPROVED", "PAYMENT_RELEASED"} <= set(store.event_types(case_id))


def test_lowercase_dashed_code_still_approves(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)
    code = inbox_code(case_id).lower()
    dashed = code[:4] + "-" + code[4:]

    outcome = service.record_family_decision_logic(case_id, "c_rohan", dashed, "APPROVE")

    assert outcome["status"] == "APPROVED"


def test_reject_with_valid_code_keeps_payment_blocked(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)

    outcome = service.record_family_decision_logic(
        case_id, "c_rohan", inbox_code(case_id), "REJECT"
    )

    case = store.cases[case_id]
    assert outcome["status"] == "REJECTED"
    assert case["payment_status"] == "BLOCKED"
    assert case["approved"] is False
    assert {"FAMILY_REJECTED", "PAYMENT_BLOCKED"} <= set(store.event_types(case_id))


def test_wrong_code_does_not_approve(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)

    outcome = service.record_family_decision_logic(case_id, "c_rohan", "AAAAAAAA", "APPROVE")

    assert outcome["error"] == "Invalid approval code"
    assert outcome["attempts_left"] == 2
    assert store.cases[case_id]["status"] == "AWAITING_FAMILY"
    assert store.cases[case_id]["payment_status"] == "HELD"
    assert "BAD_APPROVAL_CODE" in store.event_types(case_id)


def test_bad_code_audit_event_has_no_code(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)

    service.record_family_decision_logic(case_id, "c_rohan", "ZZZZZZZZ", "APPROVE")

    bad = [e for e in store.events if e["event_type"] == "BAD_APPROVAL_CODE"][0]
    assert bad["details"] == {"contact_id": "c_rohan", "attempt": 1}


def test_three_wrong_codes_lock_the_contact(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)
    good = inbox_code(case_id)

    for _ in range(3):
        service.record_family_decision_logic(case_id, "c_rohan", "AAAAAAAA", "APPROVE")

    assert store.cases[case_id]["approvals"]["c_rohan"]["used"] is True

    outcome = service.record_family_decision_logic(case_id, "c_rohan", good, "APPROVE")

    assert "error" in outcome
    assert store.cases[case_id]["status"] == "AWAITING_FAMILY"


def test_replaying_a_used_code_fails(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)
    code = inbox_code(case_id)

    service.record_family_decision_logic(case_id, "c_rohan", code, "APPROVE")
    replay = service.record_family_decision_logic(case_id, "c_rohan", code, "REJECT")

    assert replay == {"error": "Case already decided"}
    assert store.cases[case_id]["status"] == "APPROVED"


def test_expired_entry_cannot_decide(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)
    code = inbox_code(case_id)
    store.cases[case_id]["approvals"]["c_rohan"]["expires_at"] = "2000-01-01T00:00:00+00:00"

    outcome = service.record_family_decision_logic(case_id, "c_rohan", code, "APPROVE")

    assert outcome == {"error": "No active approval for this contact"}
    assert store.cases[case_id]["status"] == "AWAITING_FAMILY"
    assert service.get_family_inbox_logic(case_id, "c_rohan") == {"found": False}


def test_unknown_contact_cannot_decide(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)

    outcome = service.record_family_decision_logic(
        case_id, "c_stranger", inbox_code(case_id), "APPROVE"
    )

    assert "error" in outcome
    assert store.cases[case_id]["status"] == "AWAITING_FAMILY"


def test_contact_who_was_not_alerted_cannot_decide(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)
    rohan_code = inbox_code(case_id)

    outcome = service.record_family_decision_logic(case_id, "c_anita", rohan_code, "APPROVE")

    assert outcome == {"error": "No active approval for this contact"}


@pytest.mark.parametrize("decision", ["approve", "YES", "", None, "APPROVE "])
def test_invalid_decision_is_refused(monkeypatch, decision):
    store, case_id, _ = open_hold(monkeypatch)

    outcome = service.record_family_decision_logic(
        case_id, "c_rohan", inbox_code(case_id), decision
    )

    assert "error" in outcome
    assert store.cases[case_id]["status"] == "AWAITING_FAMILY"


def test_decision_on_unknown_case_is_refused(monkeypatch):
    install(monkeypatch)

    assert service.record_family_decision_logic(
        "case-missing", "c_rohan", "AAAAAAAA", "APPROVE"
    ) == {"error": "Case not found"}


def test_inbox_is_empty_before_alert_and_after_decision(monkeypatch):
    store = install(monkeypatch)
    cleared = service.open_protection_case_logic(OWNER, 5, 100.0, "Milk shop", False)
    assert service.get_family_inbox_logic(cleared["task_id"], "c_rohan") == {"found": False}
    assert service.get_family_inbox_logic("case-missing", "c_rohan") == {"found": False}

    _, case_id, _ = open_hold(monkeypatch, store)
    code = inbox_code(case_id)
    service.record_family_decision_logic(case_id, "c_rohan", code, "APPROVE")

    assert service.get_family_inbox_logic(case_id, "c_rohan") == {"found": False}


def test_inbox_message_uses_masked_payee(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)

    inbox = service.get_family_inbox_logic(case_id, "c_rohan")

    assert inbox["found"] is True
    assert inbox["for"] == "Rohan"
    assert "Rs 25000" in inbox["message"]
    assert "9876543210" not in inbox["message"]
    assert len(inbox["approval_code"]) == 8


def test_approval_code_only_appears_in_the_inbox(monkeypatch):
    store, case_id, opened = open_hold(monkeypatch)
    code = inbox_code(case_id)

    outputs = {
        "open": opened,
        "alert": service.alert_trusted_contact_logic(case_id, OWNER),
        "get_case": service.get_protection_case_logic(case_id, OWNER),
        "receipt": service.get_case_receipt_logic(case_id, OWNER),
        "wrong": service.record_family_decision_logic(case_id, "c_rohan", "AAAAAAAA", "APPROVE"),
        "decide": service.record_family_decision_logic(case_id, "c_rohan", code, "APPROVE"),
        "audit": store.events,
        "stored": store.cases[case_id],
    }

    for name, value in outputs.items():
        assert code not in json.dumps(value, default=str), name


def test_missing_secret_fails_closed(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)
    monkeypatch.delenv("RELAY_SHIELD_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="RELAY_SHIELD_SECRET is not set"):
        service._secret()

    with pytest.raises(RuntimeError):
        service.alert_trusted_contact_logic(case_id, OWNER)

    with pytest.raises(RuntimeError):
        service.get_family_inbox_logic(case_id, "c_rohan")

    with pytest.raises(RuntimeError):
        service.record_family_decision_logic(case_id, "c_rohan", "AAAAAAAA", "APPROVE")

    assert store.cases[case_id]["payment_status"] == "HELD"


def test_timer_failure_never_releases_money(monkeypatch):
    store = install(monkeypatch)
    monkeypatch.setattr(
        service, "schedule_resume", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    result = service.open_protection_case_logic(OWNER, 85, 25000.0, "UPI 9876543210", True)

    assert store.cases[result["task_id"]]["payment_status"] == "HELD"
    assert store.cases[result["task_id"]]["status"] == "AWAITING_FAMILY"


class RecordingTable:
    def __init__(self):
        self.calls = []

    def update_item(self, **kwargs):
        self.calls.append(kwargs)
        return {"Attributes": {"task_id": "case-1", "status": "AWAITING_FAMILY", "amount": Decimal("5")}}


def test_conditional_update_builds_nested_path_with_placeholders(monkeypatch):
    table = RecordingTable()
    monkeypatch.setattr(service, "tasks_table", table)

    service._conditional_update(
        "case-1",
        "HELD",
        {"status": "AWAITING_FAMILY", "approvals.c_rohan": {"used": False}},
        extra_condition="attribute_not_exists(approvals.#cid)",
        extra_names={"#cid": "c_rohan"},
    )

    call = table.calls[0]
    names = call["ExpressionAttributeNames"]

    assert names["#s"] == "status"
    assert "c_rohan" in names.values()
    assert "approvals" in names.values()
    assert "attribute_not_exists(approvals.#cid)" in call["ConditionExpression"]
    assert "#s = :expected_status" in call["ConditionExpression"]
    assert " status " not in f" {call['UpdateExpression']} "


def test_decision_racing_a_lockout_is_refused_by_the_conditional_update(monkeypatch):
    store, case_id, _ = open_hold(monkeypatch)
    code = inbox_code(case_id)
    stale = store.get_task(case_id)  # snapshot taken before the lockout

    # Another request locks the contact (used = True) after our read.
    store.cases[case_id]["approvals"]["c_rohan"]["used"] = True
    monkeypatch.setattr(service, "get_task", lambda _id: stale)

    outcome = service.record_family_decision_logic(case_id, "c_rohan", code, "APPROVE")

    assert outcome == {"error": "Case already decided"}
    assert store.cases[case_id]["status"] == "AWAITING_FAMILY"
    assert store.cases[case_id]["payment_status"] == "HELD"
    assert "FAMILY_APPROVED" not in store.event_types(case_id)