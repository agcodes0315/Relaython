"""Relay Shield Test 2: case policy edge cases.

Full state matrix, a hand-written decision table, invalid and hostile input,
risk mapping, action names and contact ordering.

The expectations below are written by hand on purpose: they are NOT read from
the code, so changing a rule or a transition in policy.py makes a test fail.
Plain pytest functions, no AWS, no network.
"""

import copy
import math

from relay.scam.data import get_profile
from relay.scam.policy import (
    CASE_TRANSITIONS,
    FINAL_STATES,
    assess_payment,
    contact_at,
    evaluate_scam_action,
    validate_case_transition,
)

PROFILE = get_profile("user_savita")  # payment_limit 10000

STATES = [
    "OPENED",
    "WARNED",
    "HELD",
    "AWAITING_FAMILY",
    "CLEARED",
    "BLOCKED",
    "APPROVED",
    "REJECTED",
    "EXPIRED_BLOCKED",
]

# The only 11 moves that are allowed, written by hand.
LEGAL_PAIRS = {
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
}

# ------------------------------------------------------------ state matrix


def test_all_81_ordered_pairs_match_the_hand_written_legal_set():
    for current in STATES:
        for nxt in STATES:
            allowed, _ = validate_case_transition(current, nxt)

            assert allowed is ((current, nxt) in LEGAL_PAIRS), (current, nxt)


def test_the_transition_table_is_exactly_the_legal_set():
    table_pairs = {
        (current, nxt)
        for current, exits in CASE_TRANSITIONS.items()
        for nxt in exits
    }

    assert set(CASE_TRANSITIONS.keys()) == set(STATES)
    assert table_pairs == LEGAL_PAIRS


def test_no_state_can_move_to_itself():
    for state in STATES:
        assert validate_case_transition(state, state)[0] is False


def test_unknown_states_are_refused_without_raising():
    assert validate_case_transition("NO_SUCH_STATE", "HELD")[0] is False
    assert validate_case_transition("OPENED", "NO_SUCH_STATE")[0] is False
    assert validate_case_transition("held", "AWAITING_FAMILY")[0] is False
    assert validate_case_transition("", "")[0] is False
    assert validate_case_transition(None, "HELD")[0] is False
    assert validate_case_transition("HELD", None)[0] is False
    assert validate_case_transition(["HELD"], {"x"})[0] is False


def test_final_states_have_no_exits_and_everything_else_does():
    hand_written_final = {
        "CLEARED",
        "BLOCKED",
        "APPROVED",
        "REJECTED",
        "EXPIRED_BLOCKED",
    }

    assert set(FINAL_STATES) == hand_written_final

    for state in STATES:
        has_exit = any(validate_case_transition(state, n)[0] for n in STATES)

        assert has_exit is (state not in hand_written_final), state


def test_silence_can_only_end_in_a_blocked_payment():
    # Nobody answering must never lead to a release: the only timeout exit
    # from AWAITING_FAMILY is EXPIRED_BLOCKED, and HELD cannot be approved.
    assert validate_case_transition("AWAITING_FAMILY", "EXPIRED_BLOCKED")[0] is True
    assert validate_case_transition("HELD", "APPROVED")[0] is False
    assert validate_case_transition("EXPIRED_BLOCKED", "APPROVED")[0] is False


# ---------------------------------------------------- assess_payment table

# One row per (amount, payee_is_new). Columns are the expected decision for
# three risk bands, written by hand from the rules:
#   risk 0-39   -> only the limit rule can hold
#   risk 40-69  -> WARN, unless the limit rule holds
#   risk 70-100 -> HOLD whenever money is moving (amount above 0)
#                  (amount None or 0: nothing to hold -> WARN)
#
#   amount, new payee,   low,    mid,    high
TABLE = [
    (None,   True,   "ALLOW", "WARN", "WARN"),
    (None,   False,  "ALLOW", "WARN", "WARN"),
    (0,      True,   "ALLOW", "WARN", "WARN"),
    (0,      False,  "ALLOW", "WARN", "WARN"),
    (5000,   True,   "ALLOW", "WARN", "HOLD"),
    (5000,   False,  "ALLOW", "WARN", "HOLD"),
    (10000,  True,   "ALLOW", "WARN", "HOLD"),   # exactly the limit: not over
    (10000,  False,  "ALLOW", "WARN", "HOLD"),
    (10001,  True,   "HOLD",  "HOLD", "HOLD"),   # over the limit, new payee
    (10001,  False,  "ALLOW", "WARN", "HOLD"),   # over the limit, known payee
]

LOW_RISKS = (0, 39)
MID_RISKS = (40, 69)
HIGH_RISKS = (70, 100)


def test_decision_table_all_60_combinations():
    checked = 0

    for amount, new_payee, low, mid, high in TABLE:
        for risks, expected in (
            (LOW_RISKS, low),
            (MID_RISKS, mid),
            (HIGH_RISKS, high),
        ):
            for risk in risks:
                result = assess_payment(risk, amount, new_payee, PROFILE)

                assert result["decision"] == expected, (
                    f"risk={risk} amount={amount} new_payee={new_payee}: "
                    f"expected {expected}, got {result['decision']}"
                )
                checked += 1

    assert checked == 60


def test_risk_90_with_no_amount_does_not_raise_and_warns():
    for new_payee in (True, False):
        result = assess_payment(90, None, new_payee, PROFILE)

        assert result["decision"] == "WARN"


def test_amount_exactly_at_the_limit_with_a_new_payee_is_not_held_by_the_limit():
    assert assess_payment(10, 10000, True, PROFILE)["decision"] == "ALLOW"
    assert assess_payment(45, 10000, True, PROFILE)["decision"] == "WARN"


def test_amount_over_the_limit_with_a_new_payee_is_held():
    assert assess_payment(10, 10001, True, PROFILE)["decision"] == "HOLD"
    assert assess_payment(0, 10001, True, PROFILE)["decision"] == "HOLD"


def test_amount_over_the_limit_with_a_known_payee_and_low_risk_is_allowed():
    assert assess_payment(10, 10001, False, PROFILE)["decision"] == "ALLOW"
    assert assess_payment(10, 1_000_000, False, PROFILE)["decision"] == "ALLOW"


def test_the_limit_comes_from_the_profile_not_a_hard_coded_number():
    small = dict(PROFILE, payment_limit=100)

    assert assess_payment(10, 100, True, small)["decision"] == "ALLOW"
    assert assess_payment(10, 101, True, small)["decision"] == "HOLD"
    assert assess_payment(10, 5000, True, PROFILE)["decision"] == "ALLOW"


def test_float_amounts_work():
    assert assess_payment(10, 10000.0, True, PROFILE)["decision"] == "ALLOW"
    assert assess_payment(10, 10000.01, True, PROFILE)["decision"] == "HOLD"
    assert assess_payment(70.0, 0.5, False, PROFILE)["decision"] == "HOLD"


# ------------------------------------------------------------ invalid input


def test_invalid_numbers_are_blocked_with_a_reason():
    cases = [
        (-1, 100),      # risk below 0
        (101, 100),     # risk above 100
        (50, -1),       # negative amount
        (-0.5, 100),
        (100.5, 100),
    ]

    for risk, amount in cases:
        result = assess_payment(risk, amount, False, PROFILE)

        assert result["decision"] == "BLOCK", (risk, amount)
        assert result["reasons"] and result["reasons"][0], (risk, amount)


def test_invalid_input_is_blocked_before_any_other_rule():
    # Risk 90 would be a HOLD, but the invalid amount wins.
    assert assess_payment(90, -50, True, PROFILE)["decision"] == "BLOCK"
    # A huge risk number would be a HOLD, but it is out of range.
    assert assess_payment(500, 5000, True, PROFILE)["decision"] == "BLOCK"


def test_wrong_types_do_not_crash_and_are_blocked():
    # Documented behaviour: anything that is not a real number is BLOCK.
    for bad_risk in ["50", None, True, False, float("nan"), math.inf, [50], {}]:
        result = assess_payment(bad_risk, 100, False, PROFILE)

        assert result["decision"] == "BLOCK", repr(bad_risk)

    for bad_amount in ["100", True, float("nan"), math.inf, [1]]:
        result = assess_payment(50, bad_amount, False, PROFILE)

        assert result["decision"] == "BLOCK", repr(bad_amount)


def test_a_broken_profile_is_blocked_not_trusted():
    for bad_profile in [None, {}, {"payment_limit": "10000"}, {"payment_limit": None}, "x"]:
        result = assess_payment(10, 100, False, bad_profile)

        assert result["decision"] == "BLOCK", repr(bad_profile)


def test_assess_payment_does_not_change_the_profile():
    profile = get_profile("user_savita")
    before = copy.deepcopy(profile)

    assess_payment(90, 25000, True, profile)

    assert profile == before


# ------------------------------------------------------------ risk mapping


def test_risk_mapping_for_every_decision():
    allow = assess_payment(10, 100, False, PROFILE)
    warn = assess_payment(45, 100, False, PROFILE)
    hold = assess_payment(90, 5000, True, PROFILE)
    block = assess_payment(-1, 100, False, PROFILE)

    assert (allow["decision"], allow["risk"]) == ("ALLOW", "READ_ONLY")
    assert (warn["decision"], warn["risk"]) == ("WARN", "REVERSIBLE")
    assert (hold["decision"], hold["risk"]) == ("HOLD", "SPEND")
    assert (block["decision"], block["risk"]) == ("BLOCK", "IRREVERSIBLE")


def test_every_decision_has_at_least_one_non_empty_reason():
    outcomes = [
        assess_payment(10, 100, False, PROFILE),
        assess_payment(45, 100, False, PROFILE),
        assess_payment(75, None, True, PROFILE),
        assess_payment(90, 5000, True, PROFILE),
        assess_payment(10, 20000, True, PROFILE),
        assess_payment(-1, 100, False, PROFILE),
    ]

    for result in outcomes:
        assert isinstance(result["reasons"], list)
        assert len(result["reasons"]) >= 1
        assert all(isinstance(r, str) and r.strip() for r in result["reasons"])


# ----------------------------------------------------- evaluate_scam_action

KNOWN_ACTIONS = {
    "ANALYZE_MESSAGE": ("ALLOW", "READ_ONLY"),
    "CHECK_NUMBER": ("ALLOW", "READ_ONLY"),
    "OPEN_CASE": ("ALLOW", "REVERSIBLE"),
    "ALERT_CONTACT": ("ALLOW", "REVERSIBLE"),
    "FAMILY_DECISION": ("REQUIRE_APPROVAL", "COMMITMENT"),
    "RELEASE_PAYMENT": ("REQUIRE_APPROVAL", "IRREVERSIBLE"),
}


def test_all_six_known_actions_have_the_documented_decision_and_risk():
    for action, (decision, risk) in KNOWN_ACTIONS.items():
        result = evaluate_scam_action(action)

        assert result["decision"] == decision, action
        assert result["risk"] == risk, action
        assert result["reason"], action


def test_family_decision_reason_is_the_documented_text():
    result = evaluate_scam_action("FAMILY_DECISION")

    assert result["reason"] == "Needs a valid family approval code."


def test_unknown_or_malformed_action_names_are_blocked_with_the_exact_reason():
    bad_names = [
        "analyze_message",       # lowercase
        " ANALYZE_MESSAGE ",     # padded
        "ANALYZE_MESSAGE\n",
        "Analyze_Message",
        "",
        None,
        123,
        ["OPEN_CASE"],
        "DELETE_EVERYTHING",
    ]

    for name in bad_names:
        result = evaluate_scam_action(name)

        assert result["decision"] == "BLOCK", repr(name)
        assert result["risk"] == "IRREVERSIBLE", repr(name)
        assert result["reason"] == "Unknown action is blocked by default.", repr(name)


def test_nothing_that_moves_money_is_allowed_without_approval():
    assert evaluate_scam_action("RELEASE_PAYMENT")["decision"] != "ALLOW"
    assert evaluate_scam_action("FAMILY_DECISION")["decision"] != "ALLOW"


# --------------------------------------------------------------- contact_at


def test_the_two_demo_contacts_come_back_in_order():
    first = contact_at(PROFILE, 0)
    second = contact_at(PROFILE, 1)

    assert first == {"contact_id": "c_rohan", "name": "Rohan", "order": 1}
    assert second == {"contact_id": "c_anita", "name": "Anita", "order": 2}


def test_out_of_range_and_negative_indexes_return_none():
    assert contact_at(PROFILE, 2) is None
    assert contact_at(PROFILE, 3) is None
    assert contact_at(PROFILE, -1) is None
    assert contact_at(PROFILE, 10**6) is None


def test_bad_index_types_and_bad_profiles_return_none_without_raising():
    assert contact_at(PROFILE, True) is None
    assert contact_at(PROFILE, 0.0) is None
    assert contact_at(PROFILE, "0") is None
    assert contact_at(PROFILE, None) is None
    assert contact_at(None, 0) is None
    assert contact_at({}, 0) is None
    assert contact_at({"contacts": "nope"}, 0) is None
    assert contact_at({"contacts": []}, 0) is None


def test_contacts_are_ordered_by_the_order_field_even_if_the_list_is_shuffled():
    shuffled = {
        "contacts": [
            {"contact_id": "c3", "name": "Third", "order": 3},
            {"contact_id": "c1", "name": "First", "order": 1},
            {"contact_id": "c2", "name": "Second", "order": 2},
        ]
    }

    assert [contact_at(shuffled, i)["contact_id"] for i in range(3)] == ["c1", "c2", "c3"]
    assert contact_at(shuffled, 3) is None


def test_contact_at_returns_a_copy_and_does_not_reorder_the_profile():
    shuffled = {
        "contacts": [
            {"contact_id": "c2", "name": "Second", "order": 2},
            {"contact_id": "c1", "name": "First", "order": 1},
        ]
    }
    before = copy.deepcopy(shuffled)

    contact = contact_at(shuffled, 0)
    contact["name"] = "Changed"

    assert shuffled == before
    assert contact_at(shuffled, 0)["name"] == "First"
