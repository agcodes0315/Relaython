
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

import relay.scam.service as service
from relay.scam.receipt import build_case_receipt
from scam_fakes import install

OWNER = "user_savita"

ALL_EVENT_TYPES = [
    "CASE_OPENED", "POLICY_EVALUATED", "PAYMENT_HELD", "CONTACT_ALERTED",
    "ESCALATED", "FAMILY_APPROVED", "FAMILY_REJECTED", "PAYMENT_RELEASED",
    "PAYMENT_BLOCKED", "HOLD_EXPIRED", "BAD_APPROVAL_CODE",
    "RESUME_TRIGGERED", "WAIT_SCHEDULED",
]


def make_case(**changes):
    case = {
        "task_id": "case-222",
        "kind": "scam_case",
        "owner_id": OWNER,
        "status": "APPROVED",
        "payment_status": "RELEASED",
        "risk_score": 85,
        "risk_level": "CRITICAL",
        "signals": ["otp_request", "impersonation"],
        "amount": 25000.5,
        "payee_label": "UPI 9876543210",  # deliberately unmasked
        "contacts": [
            {"contact_id": "c_rohan", "name": "Rohan", "order": 1},
            {"contact_id": "c_anita", "name": "Anita", "order": 2},
        ],
        "created_at": "2026-01-01T10:00:00+00:00",
        "decided_at": "2026-01-01T10:01:30+00:00",
    }
    case.update(changes)
    return case


def ev(event_type, ts, **details):
    return {"event_type": event_type, "timestamp": ts, "details": details}


def approved_story():
    return [
        ev("CASE_OPENED", "2026-01-01T10:00:00+00:00", risk_score=85, risk_level="CRITICAL"),
        ev("POLICY_EVALUATED", "2026-01-01T10:00:00.500000+00:00", decision="HOLD"),
        ev("PAYMENT_HELD", "2026-01-01T10:00:01+00:00", amount=25000, payee_label="UPI 98******10"),
        ev("CONTACT_ALERTED", "2026-01-01T10:00:02+00:00", contact_id="c_rohan", name="Rohan"),
        ev("FAMILY_APPROVED", "2026-01-01T10:01:30+00:00", contact_id="c_rohan", name="Rohan"),
        ev("PAYMENT_RELEASED", "2026-01-01T10:01:31+00:00", contact_id="c_rohan"),
    ]


# ------------------------------------------------------------------ secrets


def test_secret_keys_are_dropped_at_every_depth():
    events = [
        ev(
            "CONTACT_ALERTED",
            "2026-01-01T10:00:00+00:00",
            approval_code="ABCD2345",
            nested={"token": "tok-secret-1", "ok": 1},
            list=[{"secret": "hush-2", "keep": "yes"}],
        )
    ]

    receipt = build_case_receipt(make_case(), events)
    dumped = json.dumps(receipt)

    assert "ABCD2345" not in dumped
    assert "tok-secret-1" not in dumped
    assert "hush-2" not in dumped
    details = receipt["events"][0]["details"]
    assert details["nested"] == {"ok": 1}
    assert details["list"] == [{"keep": "yes"}]


def test_secret_keys_are_dropped_from_the_case_too():
    case = make_case(approval_code="ZZZZ9999", shield_secret="s3cr3t-value")

    dumped = json.dumps(build_case_receipt(case, []))

    assert "ZZZZ9999" not in dumped
    assert "s3cr3t-value" not in dumped


# ----------------------------------------------------------------- ordering


def test_events_given_out_of_order_come_back_sorted():
    events = [
        ev("FAMILY_APPROVED", "2026-01-01T10:05:00+00:00"),
        ev("CASE_OPENED", "2026-01-01T10:00:00+00:00"),
        ev("CONTACT_ALERTED", "2026-01-01T10:01:00+00:00"),
    ]

    receipt = build_case_receipt(make_case(), events)

    assert [e["event_type"] for e in receipt["events"]] == [
        "CASE_OPENED", "CONTACT_ALERTED", "FAMILY_APPROVED",
    ]


def test_events_with_the_same_timestamp_keep_their_order():
    same = "2026-01-01T10:00:00+00:00"
    events = [ev("PAYMENT_HELD", same), ev("CONTACT_ALERTED", same), ev("POLICY_EVALUATED", same)]

    receipt = build_case_receipt(make_case(), events)

    assert [e["event_type"] for e in receipt["events"]] == [
        "PAYMENT_HELD", "CONTACT_ALERTED", "POLICY_EVALUATED",
    ]


# ------------------------------------------------------------- missing data


def test_event_without_details_does_not_crash():
    receipt = build_case_receipt(
        make_case(), [{"event_type": "CASE_OPENED", "timestamp": "2026-01-01T10:00:00+00:00"}]
    )

    assert receipt["events"][0]["details"] == {}
    assert receipt["events"][0]["summary"]


def test_event_without_timestamp_gets_a_fallback_time():
    receipt = build_case_receipt(make_case(), [{"event_type": "CASE_OPENED", "details": {}}])

    assert receipt["events"][0]["timestamp"]


def test_unknown_event_type_is_still_summarized():
    receipt = build_case_receipt(
        make_case(), [ev("SOMETHING_NEW", "2026-01-01T10:00:00+00:00", a=1)]
    )

    summary = receipt["events"][0]["summary"]
    assert summary and "SOMETHING_NEW" in summary


def test_empty_events_list_gives_a_valid_receipt():
    receipt = build_case_receipt(make_case(status="HELD", payment_status="HELD"), [])

    assert receipt["event_count"] == 0
    assert receipt["events"] == []
    assert receipt["answers"]["who_decided_and_how"] == "No decision yet."
    json.dumps(receipt)


def test_garbage_inputs_do_not_raise():
    receipt = build_case_receipt(None, [None, "x", 5, {"event_type": None, "details": "oops"}])

    json.dumps(receipt)
    assert receipt["event_count"] == 1


# ---------------------------------------------------------------- summaries


@pytest.mark.parametrize("event_type", ALL_EVENT_TYPES)
def test_every_known_event_type_has_a_plain_one_line_summary(event_type):
    receipt = build_case_receipt(
        make_case(),
        [ev(event_type, "2026-01-01T10:00:00+00:00", contact_id="c_rohan", amount=100)],
    )
    summary = receipt["events"][0]["summary"]

    assert summary.strip()
    assert "\n" not in summary
    assert "{" not in summary and "}" not in summary
    assert "'contact_id'" not in summary


# ------------------------------------------------------------------- purity


def test_inputs_are_not_modified():
    case = make_case(approval_code="HIDDEN123")
    events = approved_story()
    events[3]["details"]["approval_code"] = "ABCD2345"
    case_before = copy.deepcopy(case)
    events_before = copy.deepcopy(events)

    build_case_receipt(case, events)

    assert case == case_before
    assert events == events_before


# --------------------------------------------------------------------- JSON


def test_receipt_is_json_safe_with_decimals_dates_and_sets():
    case = make_case(amount=Decimal("25000.50"), risk_score=Decimal("85"))
    events = [
        ev(
            "PAYMENT_HELD",
            "2026-01-01T10:00:00+00:00",
            amount=Decimal("25000.50"),
            when=datetime(2026, 1, 1, tzinfo=timezone.utc),
            flags={"a", "b"},
            nested={"ratio": 0.25, "items": [1, 2.5, None, True]},
        )
    ]

    receipt = build_case_receipt(case, events)
    round_trip = json.loads(json.dumps(receipt))

    assert round_trip["case"]["amount"] == 25000.5
    assert round_trip["events"][0]["details"]["nested"]["ratio"] == 0.25


# ------------------------------------------------------------------ answers


def test_approved_story_fills_the_answers():
    receipt = build_case_receipt(make_case(), approved_story())
    answers = receipt["answers"]

    assert answers["why_it_was_flagged"] == ["otp_request", "impersonation"]
    assert "c_rohan" in answers["who_decided_and_how"]
    assert "APPROVE" in answers["who_decided_and_how"]
    assert answers["who_was_alerted_and_when"][0]["name"] == "Rohan"
    assert "approved" in answers["final_outcome"].lower()
    assert answers["how_escalation_happened"] == "No escalation was needed."


def test_expired_blocked_case_says_nobody_answered():
    case = make_case(status="EXPIRED_BLOCKED", payment_status="BLOCKED", approved=False)
    events = [
        ev("CASE_OPENED", "2026-01-01T10:00:00+00:00"),
        ev("CONTACT_ALERTED", "2026-01-01T10:00:02+00:00", contact_id="c_rohan", name="Rohan"),
        ev("HOLD_EXPIRED", "2026-01-01T10:02:00+00:00"),
        ev("PAYMENT_BLOCKED", "2026-01-01T10:02:00.5+00:00"),
    ]

    answers = build_case_receipt(case, events)["answers"]

    assert answers["who_decided_and_how"] == "nobody answered"
    assert "nobody answered" in answers["final_outcome"].lower()


def test_escalated_story_fills_how_escalation_happened():
    case = make_case(status="REJECTED", payment_status="BLOCKED")
    events = [
        ev("CONTACT_ALERTED", "2026-01-01T10:00:02+00:00", contact_id="c_rohan", name="Rohan"),
        ev("ESCALATED", "2026-01-01T10:01:00+00:00", from_contact_id="c_rohan", to_contact_id="c_anita"),
        ev("FAMILY_REJECTED", "2026-01-01T10:01:30+00:00", contact_id="c_anita", name="Anita"),
    ]

    answers = build_case_receipt(case, events)["answers"]

    assert "c_rohan" in answers["how_escalation_happened"]
    assert "c_anita" in answers["how_escalation_happened"]
    assert [a["name"] for a in answers["who_was_alerted_and_when"]] == ["Rohan", "Anita"]
    assert "REJECT" in answers["who_decided_and_how"]


# ------------------------------------------------------ complaint summary


def test_complaint_summary_is_short_masked_and_secret_free():
    events = approved_story()
    events[4]["details"]["approval_code"] = "ABCD2345"

    summary = build_case_receipt(make_case(), events)["complaint_summary"]
    lines = summary.splitlines()

    assert 4 <= len(lines) <= 6
    assert "case-222" in summary
    assert "98******10" in summary
    assert "approved" in summary.lower()
    assert "9876543210" not in summary
    assert "ABCD2345" not in summary


def test_masked_payee_is_used_in_the_case_block_and_held_answer():
    receipt = build_case_receipt(make_case(), approved_story())

    assert receipt["case"]["payee_label"] == "UPI 98******10"
    assert "9876543210" not in json.dumps(receipt["answers"])


# ----------------------------------------------- get_case_receipt_logic


def test_wrong_owner_gets_case_not_found_and_no_audit_read(monkeypatch):
    store = install(monkeypatch)
    store.save_task(make_case())
    reads = []
    monkeypatch.setattr(service, "get_task_events", lambda case_id: reads.append(case_id) or [])

    assert service.get_case_receipt_logic("case-222", "someone_else") == {"error": "Case not found"}
    assert service.get_case_receipt_logic("case-missing", OWNER) == {"error": "Case not found"}
    assert reads == []


def test_owner_reads_audit_exactly_once(monkeypatch):
    store = install(monkeypatch)
    store.save_task(make_case())
    reads = []
    monkeypatch.setattr(
        service,
        "get_task_events",
        lambda case_id: reads.append(case_id) or approved_story(),
    )

    receipt = service.get_case_receipt_logic("case-222", OWNER)

    assert reads == ["case-222"]
    assert receipt["event_count"] == 6


def test_non_scam_task_is_not_exposed_as_a_case_receipt(monkeypatch):
    store = install(monkeypatch)
    store.save_task({"task_id": "task-errand", "kind": "errand", "owner_id": OWNER, "status": "OPEN"})

    assert service.get_case_receipt_logic("task-errand", OWNER) == {"error": "Case not found"}