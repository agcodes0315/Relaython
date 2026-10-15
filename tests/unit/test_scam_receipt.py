
from __future__ import annotations

import relay.scam.service as service
from relay.scam.receipt import build_case_receipt
from scam_fakes import install

OWNER = "user_savita"


def make_case(status="APPROVED", payment_status="RELEASED"):
    return {
        "task_id": "case-111",
        "kind": "scam_case",
        "owner_id": OWNER,
        "status": status,
        "payment_status": payment_status,
        "risk_score": 85,
        "risk_level": "CRITICAL",
        "signals": ["otp_request", "impersonation"],
        "amount": 25000.0,
        "payee_label": "UPI 98******10",
        "contacts": [
            {"contact_id": "c_rohan", "name": "Rohan", "order": 1},
            {"contact_id": "c_anita", "name": "Anita", "order": 2},
        ],
        "created_at": "2026-01-01T10:00:00+00:00",
        "decided_at": "2026-01-01T10:01:30+00:00",
    }


def make_events():
    return [
        {"event_type": "CASE_OPENED", "timestamp": "2026-01-01T10:00:00+00:00",
         "details": {"risk_score": 85, "risk_level": "CRITICAL"}},
        {"event_type": "PAYMENT_HELD", "timestamp": "2026-01-01T10:00:01+00:00",
         "details": {"amount": 25000.0, "payee_label": "UPI 98******10"}},
        {"event_type": "CONTACT_ALERTED", "timestamp": "2026-01-01T10:00:02+00:00",
         "details": {"contact_id": "c_rohan", "name": "Rohan"}},
        {"event_type": "FAMILY_APPROVED", "timestamp": "2026-01-01T10:01:30+00:00",
         "details": {"contact_id": "c_rohan", "name": "Rohan"}},
    ]


def test_receipt_has_the_expected_top_level_keys():
    receipt = build_case_receipt(make_case(), make_events())

    for key in ("version", "event_count", "events", "case", "answers", "complaint_summary"):
        assert key in receipt

    assert receipt["event_count"] == 4
    assert receipt["case"]["case_id"] == "case-111"


def test_every_event_has_the_fields_the_timeline_needs():
    receipt = build_case_receipt(make_case(), make_events())

    for event in receipt["events"]:
        assert event["event_type"]
        assert event["timestamp"]
        assert event["summary"]
        assert isinstance(event["details"], dict)


def test_answers_replaced_with_scam_specific_keys():
    answers = build_case_receipt(make_case(), make_events())["answers"]

    assert set(answers) == {
        "why_it_was_flagged",
        "what_was_held",
        "who_was_alerted_and_when",
        "who_decided_and_how",
        "how_escalation_happened",
        "final_outcome",
    }
    assert answers["why_it_was_flagged"] == ["otp_request", "impersonation"]


def test_approval_code_in_details_is_dropped():
    events = make_events()
    events[2]["details"]["approval_code"] = "ABCD2345"

    receipt = build_case_receipt(make_case(), events)

    assert "ABCD2345" not in str(receipt)


def test_get_case_receipt_logic_returns_a_receipt_for_the_owner(monkeypatch):
    store = install(monkeypatch)
    store.save_task(make_case())
    store.events.extend(
        {"task_id": "case-111", "event_type": e["event_type"], "details": e["details"]}
        for e in make_events()
    )

    receipt = service.get_case_receipt_logic("case-111", OWNER)

    assert receipt["case"]["status"] == "APPROVED"
    assert receipt["event_count"] == 4


def test_get_case_receipt_logic_wrong_owner_is_case_not_found(monkeypatch):
    install(monkeypatch)

    assert service.get_case_receipt_logic("case-111", OWNER) == {"error": "Case not found"}