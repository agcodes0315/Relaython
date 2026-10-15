"""Task 10 tests: Bedrock classifier with rules fallback (fake client, no network)."""
from __future__ import annotations

import relay.scam.classifier as classifier
from relay.scam.scoring import analyze_message_text
from scam_fakes import FakeClient, model_json

SCAM = "SBI bank: your account is blocked, share your OTP now to unblock it."
FRIENDLY = "Hi Mom, I will call you after lunch."


def test_model_says_scam_raises_a_low_rules_score():
    client = FakeClient(model_json(confidence=0.9))

    result = classifier.analyze_message_combined(FRIENDLY, client=client)

    assert result["risk_score"] == 90
    assert result["risk_level"] == "CRITICAL"
    assert result["recommended_action"] == "HOLD_PAYMENTS"
    assert result["source"] == "rules+model"
    assert result["model_used"] is True
    assert any(s["name"] == "model_otp_phishing" for s in result["signals"])


def test_model_signal_has_the_planned_weight_and_evidence():
    result = classifier.analyze_message_combined(
        FRIENDLY, client=FakeClient(model_json(confidence=0.9))
    )
    signal = next(s for s in result["signals"] if s["name"].startswith("model_"))

    assert signal == {"name": "model_otp_phishing", "weight": 36, "evidence": "model assessment"}


def test_model_never_lowers_a_high_rules_score():
    rules = analyze_message_text(SCAM)
    client = FakeClient(model_json(is_scam=False, confidence=0.99, scam_type="none"))

    result = classifier.analyze_message_combined(SCAM, client=client)

    assert result["risk_score"] == rules["risk_score"]
    assert result["risk_score"] >= 70


def test_bad_json_falls_back_to_rules():
    result = classifier.analyze_message_combined(SCAM, client=FakeClient("not json at all"))

    assert result["source"] == "rules"
    assert result["model_used"] is False
    assert result["risk_score"] == analyze_message_text(SCAM)["risk_score"]


def test_client_error_falls_back_to_rules_without_raising():
    client = FakeClient(raises=TimeoutError("slow"))

    result = classifier.analyze_message_combined(SCAM, client=client)

    assert result["source"] == "rules"
    assert result["model_used"] is False


def test_no_client_and_no_api_key_gives_rules_only(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = classifier.analyze_message_combined(SCAM)

    assert result["source"] == "rules"
    assert result["risk_score"] == analyze_message_text(SCAM)["risk_score"]


def test_result_keeps_every_rules_field_and_adds_two():
    result = classifier.analyze_message_combined(SCAM, client=FakeClient(model_json()))

    for key in (
        "risk_score", "risk_level", "signals", "explanation",
        "recommended_action", "advice", "source", "model_used",
    ):
        assert key in result


def test_score_never_exceeds_100():
    result = classifier.analyze_message_combined(SCAM, client=FakeClient(model_json(confidence=1.0)))

    assert result["risk_score"] <= 100