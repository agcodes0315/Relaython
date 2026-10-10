# ADD THESE IMPORTS BESIDE YOUR EXISTING relay.* IMPORTS

from relay.home_assets import (
    build_service_handoff,
    check_asset_warranty,
    get_home_asset,
    list_home_assets,
    troubleshoot_asset,
)


# ADD THESE AFTER YOUR EXISTING MCP TOOL DEFINITIONS

@mcp.tool()
def list_household_assets() -> list[dict]:
    return list_home_assets()


@mcp.tool()
def get_household_asset(asset_id: str) -> dict:
    return get_home_asset(asset_id)


@mcp.tool()
def check_warranty(asset_id: str, as_of_date: str | None = None) -> dict:
    return check_asset_warranty(asset_id, as_of_date)


@mcp.tool()
def troubleshoot_home_asset(asset_id: str, symptoms: str) -> dict:
    return troubleshoot_asset(asset_id, symptoms)


@mcp.tool()
def prepare_service_from_asset(
    asset_id: str,
    symptoms: str,
    budget: float,
    deadline: str,
    excluded_days: list[str] | None = None,
) -> dict:
    return build_service_handoff(
        asset_id=asset_id,
        symptoms=symptoms,
        budget=budget,
        deadline=deadline,
        excluded_days=excluded_days,
    )


@mcp.resource(
    "relay://home/assets",
    name="relay_home_assets",
    title="Relay Home Asset Vault",
    description="Demo household purchase, model, location and warranty context.",
    mime_type="application/json",
)
def home_assets_resource() -> list[dict]:
    return list_home_assets()


@mcp.resource(
    "relay://home/assets/{asset_id}",
    name="relay_home_asset",
    title="Relay Home Asset",
    description="Context for one household asset known to Relay.",
    mime_type="application/json",
)
def home_asset_resource(asset_id: str) -> dict:
    return get_home_asset(asset_id)


@mcp.prompt(
    name="resolve_home_issue",
    title="Resolve a household product issue",
    description="Guide an agent from asset context through warranty, safe troubleshooting and durable service.",
)
def resolve_home_issue(asset_id: str, symptoms: str) -> str:
    return f'''Resolve this home issue with Relay.

Asset ID: {asset_id}
Symptoms: {symptoms}

Required workflow:
1. Read asset context.
2. Check warranty.
3. Offer only conservative, non-invasive troubleshooting.
4. Escalate electrical/fire-risk symptoms.
5. If service is needed, collect budget, deadline and excluded days.
6. Build the service handoff and create a durable Relay errand.
7. Search only providers satisfying the contract.
8. Require explicit human approval before spend or booking.
9. If a provider fails, invalidate approval, reapply constraints and require fresh approval.
10. Preserve audit and durable-resume behavior.

Never invent purchase metadata, warranty state, prices, availability or approval.'''
