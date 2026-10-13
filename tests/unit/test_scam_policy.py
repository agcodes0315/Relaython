"""Relay Shield Task 2: case policy and state machine (core tests).

Plain pytest functions, no AWS, no network. The full decision table and the
hostile-input cases live in test_scam_policy_edge.py.
"""

from relay.scam.data import get_profile
from relay.scam.policy import (
    CASE_TRANSITIONS,
    FINAL_STATES,
    assess_payment,
    contact_at,
    evaluate_scam_action,
    is_final_state,
    validate_case_transition,
)

PROFILE = get_profile("user_savita")  # payment_limit 10000

LEGAL = [
    ("OPENED", "CLEARED"),
    ("OPENED", "WARNED"),
    ("OPENED", "HELD"),
    ("OPENED", "BLOCKED"),
    ("WARNED", "HELD"),
    ("WARNED", "CLEARED"),
    ("HELD", "AWAITING_FAMILY"),
    ("HELD", "BLOCKED"),
    ("AWAITING_FAMILY", "APPROVED"),
    ("AWAITING_FAMILY", "REJECTED"),
    ("AWAITING_FAMILY", "EXPIRED_BLOCKED"),
]

ILLEGAL = [
    ("HELD", "APPROVED"),
    ("HELD", "REJECTED"),
    ("OPENED", "AWAITING_FAMILY"),
    ("OPENED", "APPROVED"),
    ("WARNED", "AWAITING_FAMILY"),
    ("AWAITING_FAMILY", "HELD"),
    ("AWAITING_FAMILY", "CLEARED"),
    ("APPROVED", "REJECTED"),
    ("REJECTED", "APPROVED"),
    ("EXPIRED_BLOCKED", "APPROVED"),
    ("BLOCKED", "OPENED"),
    ("CLEARED", "HELD"),
]

FINAL = ["CLEARED", "BLOCKED", "APPROVED", "REJECTED", "EXPIRED_BLOCKED"]


def test_every_legal_transition_is_allowed():
    for current, nxt in LEGAL:
        allowed, message = validate_case_transition(current, nxt)

        assert allowed is True, (current, nxt)
        assert message == "Transition allowed."


def test_every_illegal_transition_is_refused():
    for current, nxt in ILLEGAL:
        allowed, _ = validate_case_transition(current, nxt)

        assert allowed is False, (current, nxt)


def test_refusal_message_has_the_documented_format():
    allowed, message = validate_case_transition("HELD", "APPROVED")

    assert allowed is False
    assert message == "Invalid case transition: HELD -> APPROVED"


def test_final_states_have_no_exits():
    for state in FINAL:
        assert CASE_TRANSITIONS[state] == set()
        assert is_final_state(state) is True

    assert FINAL_STATES == frozenset(FINAL)


def test_non_final_states_are_not_final():
    for state in ["OPENED", "WARNED", "HELD", "AWAITING_FAMILY"]:
        assert is_final_state(state) is False


def test_risk_boundaries_at_39_40_69_70():
    # Small payment to a known payee: only the risk score matters.
    assert assess_payment(39, 100, False, PROFILE)["decision"] == "ALLOW"
    assert assess_payment(40, 100, False, PROFILE)["decision"] == "WARN"
    assert assess_payment(69, 100, False, PROFILE)["decision"] == "WARN"
    assert assess_payment(70, 100, False, PROFILE)["decision"] == "HOLD"


def test_payment_limit_boundary_is_strictly_greater_than():
    # Exactly the limit is allowed; one rupee more to a new payee is held.
    assert assess_payment(10, 10000, True, PROFILE)["decision"] == "ALLOW"
    assert assess_payment(10, 10001, True, PROFILE)["decision"] == "HOLD"


def test_over_limit_to_a_known_payee_is_allowed():
    assert assess_payment(10, 50000, False, PROFILE)["decision"] == "ALLOW"


def test_high_risk_with_no_amount_does_not_crash_and_warns():
    result = assess_payment(90, None, True, PROFILE)

    assert result["decision"] == "WARN"


def test_invalid_input_is_blocked():
    assert assess_payment(-1, 100, False, PROFILE)["decision"] == "BLOCK"
    assert assess_payment(101, 100, False, PROFILE)["decision"] == "BLOCK"
    assert assess_payment(50, -1, False, PROFILE)["decision"] == "BLOCK"


def test_every_decision_has_a_reason_and_a_risk_level():
    cases = [(10, 100, False), (45, 100, False), (90, 5000, True), (-5, 1, True)]

    for risk, amount, new_payee in cases:
        result = assess_payment(risk, amount, new_payee, PROFILE)

        assert set(result.keys()) == {"decision", "risk", "reasons"}
        assert result["reasons"]
        assert all(isinstance(r, str) and r for r in result["reasons"])


def test_unknown_action_is_blocked():
    result = evaluate_scam_action("DELETE_EVERYTHING")

    assert result["decision"] == "BLOCK"
    assert result["reason"] == "Unknown action is blocked by default."


def test_known_actions_have_the_documented_decisions():
    assert evaluate_scam_action("ANALYZE_MESSAGE")["decision"] == "ALLOW"
    assert evaluate_scam_action("CHECK_NUMBER")["decision"] == "ALLOW"
    assert evaluate_scam_action("OPEN_CASE")["decision"] == "ALLOW"
    assert evaluate_scam_action("ALERT_CONTACT")["decision"] == "ALLOW"
    assert evaluate_scam_action("FAMILY_DECISION")["decision"] == "REQUIRE_APPROVAL"
    assert evaluate_scam_action("RELEASE_PAYMENT")["decision"] == "REQUIRE_APPROVAL"


def test_contacts_come_back_in_order():
    assert contact_at(PROFILE, 0)["contact_id"] == "c_rohan"
    assert contact_at(PROFILE, 1)["contact_id"] == "c_anita"


def test_contact_beyond_the_end_is_none():
    assert contact_at(PROFILE, 2) is None
    assert contact_at(PROFILE, 99) is None
