"""Relay Shield Task 1: scoring engine (core tests).

Plain pytest functions, no AWS, no network. Edge cases live in
test_scam_scoring_edge.py.
"""

from relay.scam.data import DEMO_PROFILES, get_profile
from relay.scam.scoring import (
    action_for,
    analyze_message_text,
    check_number,
    level_for,
    mask_digits,
    normalize_number,
)

SCAM_MESSAGE = (
    "This is SBI bank. Your account will be blocked today. "
    "Share your OTP immediately to unblock."
)

RESULT_KEYS = {
    "risk_score",
    "risk_level",
    "signals",
    "explanation",
    "recommended_action",
    "advice",
}


def test_otp_plus_bank_message_is_high_or_critical():
    result = analyze_message_text(SCAM_MESSAGE)

    assert result["risk_level"] in ("HIGH", "CRITICAL")
    assert result["risk_score"] >= 50


def test_otp_plus_bank_message_recommends_holding_payments():
    result = analyze_message_text(SCAM_MESSAGE)

    assert result["recommended_action"] == "HOLD_PAYMENTS"


def test_friendly_message_is_low():
    result = analyze_message_text(
        "Hi Mom, I will call you after lunch. Did you take your medicines?"
    )

    assert result["risk_level"] == "LOW"
    assert result["risk_score"] < 25
    assert result["signals"] == []


def test_result_has_exactly_the_documented_keys():
    result = analyze_message_text(SCAM_MESSAGE)

    assert set(result.keys()) == RESULT_KEYS

    for signal in result["signals"]:
        assert set(signal.keys()) == {"name", "weight", "evidence"}


def test_evidence_is_never_longer_than_40_characters():
    result = analyze_message_text(SCAM_MESSAGE * 5)

    assert result["signals"]

    for signal in result["signals"]:
        assert len(signal["evidence"]) <= 40


def test_digits_in_evidence_are_masked():
    result = analyze_message_text(
        "Pay Rs 123456789 fine now, call 9876543210 or you will be arrested"
    )

    assert result["signals"]

    for signal in result["signals"]:
        assert "123456789" not in signal["evidence"]
        assert "9876543210" not in signal["evidence"]


def test_mask_digits_keeps_first_two_and_last_two():
    assert mask_digits("9876543210") == "98******10"
    assert mask_digits("call 9876543210 now") == "call 98******10 now"
    assert mask_digits("12345") == "12*45"


def test_mask_digits_leaves_short_numbers_alone():
    assert mask_digits("code 1234 ok") == "code 1234 ok"
    assert mask_digits("") == ""


def test_normalization_handles_country_code_and_spaces():
    assert normalize_number("+91 90000 00001") == "9000000001"


def test_unknown_number_returns_unknown():
    result = check_number("9876543210")

    assert result["found"] is False
    assert result["reputation"] == "UNKNOWN"
    assert result["reports"] == 0


def test_known_scam_number_is_found():
    result = check_number("+91 90000 00001")

    assert result["found"] is True
    assert result["reputation"] == "KNOWN_SCAM"
    assert result["reports"] > 0
    assert result["number_masked"] == "90******01"


def test_scoring_is_deterministic():
    first = analyze_message_text(SCAM_MESSAGE)
    second = analyze_message_text(SCAM_MESSAGE)

    assert first == second


def test_score_never_exceeds_100():
    result = analyze_message_text(SCAM_MESSAGE * 20)

    assert 0 <= result["risk_score"] <= 100


def test_level_and_action_helpers_match_the_documented_thresholds():
    assert level_for(0) == "LOW"
    assert level_for(25) == "MEDIUM"
    assert level_for(50) == "HIGH"
    assert level_for(75) == "CRITICAL"

    assert action_for(0) == "NONE"
    assert action_for(40) == "WARN"
    assert action_for(70) == "HOLD_PAYMENTS"


def test_demo_profile_exists_with_two_ordered_contacts():
    profile = get_profile("user_savita")

    assert profile["payment_limit"] == 10000
    assert profile["cooling_off_minutes"] == 30
    assert [c["contact_id"] for c in profile["contacts"]] == ["c_rohan", "c_anita"]
    assert "user_savita" in DEMO_PROFILES
