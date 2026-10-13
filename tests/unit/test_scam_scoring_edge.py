"""Relay Shield Test 1: scoring engine edge cases.

Boundaries, cap and combination rule, robustness, false positives, privacy,
monotonic scoring, number handling and data copies.
Plain pytest functions, no AWS, no network.
"""

import json
import random
import re
import time

from relay.scam.data import DEMO_PROFILES, get_profile
from relay.scam.scoring import (
    action_for,
    analyze_message_text,
    check_number,
    level_for,
    normalize_number,
)

RESULT_KEYS = {
    "risk_score",
    "risk_level",
    "signals",
    "explanation",
    "recommended_action",
    "advice",
}

ALL_SIGNAL_NAMES = {
    "otp_request",
    "impersonation",
    "urgency",
    "payment_demand",
    "remote_access",
    "suspicious_link",
    "prize_lottery",
    "kyc_update",
    "threat",
}


def assert_valid_result(result):
    """Every result, for any input, must have this exact shape."""
    assert set(result.keys()) == RESULT_KEYS
    assert isinstance(result["risk_score"], int)
    assert 0 <= result["risk_score"] <= 100
    assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert result["recommended_action"] in ("NONE", "WARN", "HOLD_PAYMENTS")
    assert isinstance(result["explanation"], str) and result["explanation"]
    assert isinstance(result["advice"], list) and result["advice"]
    assert all(isinstance(line, str) for line in result["advice"])
    assert isinstance(result["signals"], list)

    for signal in result["signals"]:
        assert set(signal.keys()) == {"name", "weight", "evidence"}
        assert isinstance(signal["weight"], int)
        assert len(signal["evidence"]) <= 40


def names(result):
    return {s["name"] for s in result["signals"]}


# ------------------------------------------------------------ boundaries


def test_level_thresholds_at_24_25_49_50_74_75():
    assert level_for(24) == "LOW"
    assert level_for(25) == "MEDIUM"
    assert level_for(49) == "MEDIUM"
    assert level_for(50) == "HIGH"
    assert level_for(74) == "HIGH"
    assert level_for(75) == "CRITICAL"


def test_action_thresholds_at_39_40_69_70():
    assert action_for(39) == "NONE"
    assert action_for(40) == "WARN"
    assert action_for(69) == "WARN"
    assert action_for(70) == "HOLD_PAYMENTS"


def test_real_messages_land_exactly_on_the_boundaries():
    # (message, expected score, expected level, expected action)
    cases = [
        ("This is SBI customer care.", 25, "MEDIUM", "NONE"),
        ("Please share your OTP.", 40, "MEDIUM", "WARN"),
        ("This is SBI customer care. Your account will be blocked.", 50, "HIGH", "WARN"),
        (
            "CBI officer here. Arrest warrant issued. "
            "Pay Rs 50000 fine now or you will be arrested",
            70,
            "HIGH",
            "HOLD_PAYMENTS",
        ),
        ("Please share your OTP and install AnyDesk.", 75, "CRITICAL", "HOLD_PAYMENTS"),
    ]

    for message, score, level, action in cases:
        result = analyze_message_text(message)

        assert result["risk_score"] == score, message
        assert result["risk_level"] == level, message
        assert result["recommended_action"] == action, message


# ------------------------------------------------- cap and combination rule


def test_message_with_every_signal_scores_exactly_100():
    message = (
        "This is SBI customer care. Share your OTP immediately. "
        "Your account will be blocked and your KYC is pending. "
        "Pay the processing fee of Rs 500 now. Install AnyDesk. "
        "Click the link http://bit.ly/abc to claim your prize in the lucky draw."
    )

    result = analyze_message_text(message)
    total_weight = sum(s["weight"] for s in result["signals"])

    assert ALL_SIGNAL_NAMES <= names(result)
    assert total_weight > 100  # proves the cap is what keeps it at 100
    assert result["risk_score"] == 100
    assert result["risk_level"] == "CRITICAL"


def test_otp_request_plus_impersonation_scores_at_least_85():
    messages = [
        "SBI: share your OTP",
        "This is HDFC bank. Please send your CVV.",
        "Bank officer here. Tell me your OTP.",
    ]

    for message in messages:
        result = analyze_message_text(message)

        assert {"otp_request", "impersonation"} <= names(result), message
        assert result["risk_score"] >= 85, message


def test_otp_request_alone_does_not_trigger_the_combination_rule():
    result = analyze_message_text("Please share your OTP.")

    assert names(result) == {"otp_request"}
    assert result["risk_score"] == 40


# ------------------------------------------------------------ robustness


def test_empty_and_whitespace_text_do_not_raise():
    for text in ["", "   ", "\n\t  \n", None]:
        result = analyze_message_text(text)

        assert_valid_result(result)
        assert result["risk_score"] == 0
        assert result["risk_level"] == "LOW"


def test_20000_characters_finish_quickly():
    long_benign = "Hello, how are you today? " * 800
    long_scam = "Share your OTP. This is SBI bank. " * 600

    for text in [long_benign[:20000], long_scam[:20000], "a b c d " * 2500]:
        started = time.perf_counter()
        result = analyze_message_text(text)
        elapsed = time.perf_counter() - started

        assert_valid_result(result)
        assert elapsed < 2.0


def test_hindi_and_mixed_scripts_do_not_raise():
    messages = [
        "आपका खाता बंद हो जाएगा, कृपया अपना ओटीपी बताएं",
        "नमस्ते माँ, मैं शाम को फोन करूँगा",
        "Hello माँ, please share OTP 😀",
    ]

    for message in messages:
        assert_valid_result(analyze_message_text(message))


def test_mixed_case_is_detected():
    lower = analyze_message_text("share your otp. this is sbi bank.")
    upper = analyze_message_text("SHARE YOUR OTP. THIS IS SBI BANK.")
    mixed = analyze_message_text("ShArE yOuR oTp. ThIs Is SbI bAnK.")

    assert lower["risk_score"] == upper["risk_score"] == mixed["risk_score"]
    assert lower["risk_score"] >= 85


def test_spaced_out_otp_is_still_detected():
    for message in [
        "Bank officer here. Please send your O T P now",
        "Bank officer here. Please send your O.T.P now",
        "Bank officer here. Please send your o-t-p now",
    ]:
        result = analyze_message_text(message)

        assert "otp_request" in names(result), message
        assert result["risk_score"] >= 85, message


def test_200_random_strings_never_raise():
    rng = random.Random(42)
    alphabet = (
        "abcdefghijklmnopqrstuvwxyz ABCDEFGHIJ0123456789.,!?-+'\n\t"
        "\u20b9\u0913\u091f\u0940\u092a\u0940\U0001f600"
    )

    for _ in range(200):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 400)))

        assert_valid_result(analyze_message_text(text))


def test_sender_argument_is_accepted_in_every_form():
    for sender in [None, "", "VM-SBIINB", "+91 90000 00001", "abc", 12345]:
        assert_valid_result(analyze_message_text("Hello there", sender))


# -------------------------------------------------------- false positives


def test_real_bank_otp_message_is_not_a_payment_hold():
    result = analyze_message_text("Your OTP is 482913. Do not share it with anyone.")

    assert result["risk_score"] < 70
    assert result["recommended_action"] != "HOLD_PAYMENTS"
    assert "otp_request" not in names(result)


def test_bank_warnings_about_otp_are_not_scams():
    warnings = [
        "Never share your OTP with anyone, including bank staff.",
        "Please do not share your PIN or CVV with anyone.",
        "Don't ever share your OTP.",
        "Your OTP is 123456. Never share it with anyone.",
    ]

    for message in warnings:
        result = analyze_message_text(message)

        assert result["recommended_action"] != "HOLD_PAYMENTS", message
        assert "otp_request" not in names(result), message


def test_normal_family_chat_is_low():
    messages = [
        "Hi Mom, I will call you after lunch. Did you take your medicines?",
        "Dinner at 8? I'm at the bank, will be late",
        "You won the cricket match today, great game!",
        "Please share your pin code for delivery",
        "Happy birthday! See you on Sunday.",
    ]

    for message in messages:
        result = analyze_message_text(message)

        assert result["risk_level"] == "LOW", message


def test_a_small_money_request_between_family_stays_low():
    result = analyze_message_text("Please send me Rs 500 for groceries")

    assert result["risk_level"] == "LOW"
    assert result["recommended_action"] == "NONE"


# ---------------------------------------------------------------- privacy


def test_evidence_is_short_and_digits_are_masked():
    message = (
        "This is SBI bank. Share your OTP 482913 or call 9876543210 now. "
        "Pay Rs 123456789 fine. Your account will be blocked immediately."
    )
    result = analyze_message_text(message)

    assert result["signals"]

    for signal in result["signals"]:
        evidence = signal["evidence"]

        assert len(evidence) <= 40
        assert not re.search(r"\d{5,}", evidence)
        assert "482913" not in evidence
        assert "9876543210" not in evidence


def test_the_full_message_and_its_secrets_never_appear_in_the_result():
    message = (
        "This is SBI bank. Share your OTP 482913 or call 9876543210 now. "
        "Pay Rs 123456789 fine. Your account will be blocked immediately."
    )
    dumped = json.dumps(analyze_message_text(message))

    assert message not in dumped
    assert "482913" not in dumped
    assert "9876543210" not in dumped
    assert "123456789" not in dumped


# --------------------------------------------------------------- monotonic

BASE_MESSAGES = [
    "Hello, how are you?",
    "Your OTP is 482913. Do not share it with anyone.",
    "Dinner at 8?",
    "This is SBI bank.",
]

SCAM_SENTENCES = [
    "Please share your OTP.",
    "This is SBI customer care.",
    "Do it immediately.",
    "Pay the processing fee of Rs 500.",
    "Install AnyDesk.",
    "Click the link http://bit.ly/abc",
    "You have won a lottery prize.",
    "Your KYC is pending.",
    "Your account will be blocked.",
]


def test_adding_a_scam_sentence_never_lowers_the_score():
    for base in BASE_MESSAGES:
        base_score = analyze_message_text(base)["risk_score"]

        for sentence in SCAM_SENTENCES:
            combined = analyze_message_text(base + " " + sentence)["risk_score"]

            assert combined >= base_score, (base, sentence)


def test_adding_signals_one_by_one_never_lowers_the_score():
    text = "Hello there."
    previous = analyze_message_text(text)["risk_score"]

    for sentence in SCAM_SENTENCES:
        text = text + " " + sentence
        score = analyze_message_text(text)["risk_score"]

        assert score >= previous, sentence
        previous = score

    assert previous == 100


# ----------------------------------------------------------------- numbers


def test_number_formats_normalize_to_the_same_value():
    variants = ["+91-90000-00001", "09000000001", "9000000001", "90000 00001"]

    assert {normalize_number(v) for v in variants} == {"9000000001"}


def test_every_format_of_a_known_number_is_found():
    for variant in ["+91-90000-00001", "09000000001", "9000000001", "90000 00001"]:
        result = check_number(variant)

        assert result["found"] is True, variant
        assert result["reputation"] == "KNOWN_SCAM", variant


def test_junk_numbers_return_unknown_without_raising():
    for junk in ["abc", "", "   ", None, "+++", "12", "98765432101234567890"]:
        result = check_number(junk)

        assert result["found"] is False
        assert result["reputation"] == "UNKNOWN"
        assert result["reports"] == 0


def test_masked_number_never_equals_the_input_digits():
    for number in ["9876543210", "9000000001", "+91 98765 43210", "123", "12345"]:
        digits = normalize_number(number)
        masked = check_number(number)["number_masked"]

        assert masked != digits, number
        assert digits not in masked, number


def test_masked_number_hides_the_middle_digits():
    assert check_number("9876543210")["number_masked"] == "98******10"


# -------------------------------------------------------------------- data


def test_get_profile_returns_a_deep_copy():
    profile = get_profile("user_savita")

    profile["payment_limit"] = 1
    profile["contacts"].append({"contact_id": "x", "name": "X", "order": 9})
    profile["contacts"][0]["name"] = "Changed"

    fresh = get_profile("user_savita")

    assert fresh["payment_limit"] == 10000
    assert len(fresh["contacts"]) == 2
    assert fresh["contacts"][0]["name"] == "Rohan"
    assert DEMO_PROFILES["user_savita"]["payment_limit"] == 10000
    assert len(DEMO_PROFILES["user_savita"]["contacts"]) == 2


def test_unknown_owner_returns_none():
    assert get_profile("nobody") is None
    assert get_profile("") is None
    assert get_profile(None) is None
