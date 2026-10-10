from relay.home_assets import (
    build_service_handoff,
    check_asset_warranty,
    get_home_asset,
    list_home_assets,
    troubleshoot_asset,
)


def test_asset_vault_contains_demo_ac():
    assert "asset_ac_001" in {x["asset_id"] for x in list_home_assets()}


def test_get_known_asset():
    result = get_home_asset("asset_ac_001")
    assert result["found"] is True
    assert result["asset"]["model_number"] == "CB-24X"


def test_warranty_active_for_demo_date():
    result = check_asset_warranty("asset_ac_001", "2026-10-10")
    assert result["warranty_active"] is True


def test_warranty_expired_after_demo_expiry():
    result = check_asset_warranty("asset_ac_001", "2027-03-13")
    assert result["warranty_active"] is False


def test_safe_troubleshooting():
    result = troubleshoot_asset("asset_ac_001", "The AC is not cooling well")
    assert result["high_risk"] is False


def test_high_risk_escalates():
    result = troubleshoot_asset("asset_ac_001", "There is a burning smell and sparking")
    assert result["high_risk"] is True
    assert result["can_continue_basic_troubleshooting"] is False


def test_handoff_matches_existing_contract():
    result = build_service_handoff(
        "asset_ac_001",
        "Not cooling",
        2000,
        "2026-10-10",
        ["Thursday"],
    )
    assert result["ready"] is True
    assert result["next_tool"] == "create_errand"
    assert result["service_contract"]["budget"] == 2000.0
