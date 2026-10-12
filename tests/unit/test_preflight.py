from relay.preflight import assess_action_risk, clarify_delegation


def test_missing_budget_requests_clarification():
    result = clarify_delegation(
        goal="Get my AC serviced",
        budget=None,
        deadline="2026-10-10",
        excluded_days=["Thursday"],
    )
    assert result["ready"] is False
    assert "budget" in result["missing_fields"]
    assert result["questions"]


def test_complete_contract_is_ready():
    result = clarify_delegation(
        goal="Get my AC serviced",
        budget=2000,
        deadline="2026-10-10",
        excluded_days=["Thursday"],
    )
    assert result["ready"] is True
    assert result["missing_fields"] == []
    assert result["normalized_contract"]["budget"] == 2000.0


def test_invalid_budget_is_rejected():
    result = clarify_delegation(
        goal="Get my AC serviced",
        budget=-1,
        deadline="2026-10-10",
        excluded_days=[],
    )
    assert result["ready"] is False
    assert "budget" in result["missing_fields"]


def test_search_is_low_risk():
    result = assess_action_risk("SEARCH")
    assert result["tier"] == "LOW"
    assert result["human_approval_required"] is False


def test_booking_requires_human_approval():
    result = assess_action_risk("BOOK")
    assert result["tier"] == "HIGH"
    assert result["human_approval_required"] is True


def test_unknown_action_defaults_safe():
    result = assess_action_risk("TRANSFER_ALL_FUNDS")
    assert result["known_action"] is False
    assert result["human_approval_required"] is True
