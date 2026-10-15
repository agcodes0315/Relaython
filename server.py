import os

from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from relay.home_assets import (
    build_service_handoff,
    check_asset_warranty,
    get_home_asset,
    list_home_assets,
    troubleshoot_asset,
)
from relay.preflight import (
    assess_action_risk as assess_action_risk_logic,
    clarify_delegation as clarify_delegation_logic,
)
from relay.scam.data import get_profile as get_shield_profile
from relay.scam.policy import assess_payment as assess_shield_payment
from relay.scam.scoring import (
    analyze_message_text as analyze_message_logic,
    check_number as check_number_logic,
)
from relay.scam.service import (
    alert_trusted_contact_logic,
    get_case_receipt_logic,
    get_family_inbox_logic,
    get_protection_case_logic,
    open_protection_case_logic,
    record_family_decision_logic,
)
from relay.recovery import (
    restore_provider as restore_provider_logic,
    simulate_provider_failure,
)
from relay.scheduler import schedule_resume_in_minutes
from relay.tools import (
    approve_booking_logic,
    create_errand_logic,
    find_providers_logic,
    get_audit_log_logic,
    get_errand_logic,
    propose_options_logic,
    select_provider_logic,
)


def allowed_hosts() -> list[str]:
    """localhost always; deployed hostnames come from RELAY_PUBLIC_HOST (comma-separated)."""
    hosts = ["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"]
    for host in os.environ.get("RELAY_PUBLIC_HOST", "").split(","):
        host = host.strip()
        if host:
            hosts += [host, f"{host}:*"]
    return hosts

mcp = MCPServer("Relay")


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": "relay-mcp",
            "security": "host-and-origin-validation-enabled",
            "capabilities": {
                "clarification": True,
                "risk_policy": True,
                "durable_resume": True,
                "failure_recovery": True,
                "scam_shield": True,
            },
        }
    )


@mcp.tool()
def clarify_delegation(
    goal: str | None = None,
    budget: float | None = None,
    deadline: str | None = None,
    excluded_days: list[str] | None = None,
) -> dict:
    return clarify_delegation_logic(
        goal=goal,
        budget=budget,
        deadline=deadline,
        excluded_days=excluded_days,
    )


@mcp.tool()
def assess_action_risk(action: str) -> dict:
    return assess_action_risk_logic(action)


@mcp.tool()
def create_errand(
    goal: str,
    budget: float,
    deadline: str,
    excluded_days: list[str],
) -> dict:
    return create_errand_logic(goal, budget, deadline, excluded_days)


@mcp.tool()
def get_errand(task_id: str) -> dict:
    return get_errand_logic(task_id)


@mcp.tool()
def find_providers(task_id: str) -> dict:
    return find_providers_logic(task_id)


@mcp.tool()
def propose_options(task_id: str) -> dict:
    return propose_options_logic(task_id)


@mcp.tool()
def select_provider(task_id: str, provider_id: str) -> dict:
    return select_provider_logic(task_id, provider_id)


@mcp.tool()
def approve_booking(task_id: str, approve: bool) -> dict:
    return approve_booking_logic(task_id, approve)


@mcp.tool()
def get_audit_log(task_id: str) -> list[dict]:
    return get_audit_log_logic(task_id)


@mcp.tool()
def simulate_provider_failure_tool(task_id: str) -> dict:
    return simulate_provider_failure(task_id)


@mcp.tool()
def restore_provider(provider_id: str) -> dict:
    return restore_provider_logic(provider_id)


@mcp.tool()
def schedule_task_resume(task_id: str, minutes: int = 2) -> dict:
    return schedule_resume_in_minutes(task_id=task_id, minutes=minutes)



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


# ---------------------------------------------------------------------------
# Relay Shield: scam protection for families
# ---------------------------------------------------------------------------


@mcp.tool()
def analyze_message(text: str, sender: str | None = None) -> dict:
    """Score a suspicious message for scam signals.

    Risk tier: READ_ONLY. Nothing is stored and nothing is changed.
    """
    return analyze_message_logic(text, sender)


@mcp.tool()
def check_number(number: str) -> dict:
    """Look up a phone number in the synthetic reputation list.

    Risk tier: READ_ONLY. The number is returned masked.
    """
    return check_number_logic(number)


@mcp.tool()
def assess_scam_risk(
    owner_id: str,
    risk_score: int,
    amount: float | None = None,
    payee_is_new: bool = False,
) -> dict:
    """Decide ALLOW, WARN, HOLD or BLOCK for a payment.

    Risk tier: READ_ONLY. This only evaluates the policy; it does not hold
    anything. Use open_protection_case to act on a HOLD.
    """
    profile = get_shield_profile(owner_id)

    if profile is None:
        return {"error": "Unknown protected user"}

    result = assess_shield_payment(
        risk_score=risk_score,
        amount=amount,
        payee_is_new=payee_is_new,
        profile=profile,
    )

    return {
        "owner_id": owner_id,
        "decision": result["decision"],
        "risk": result["risk"],
        "reasons": result["reasons"],
        "payment_limit": profile["payment_limit"],
    }


@mcp.tool()
def open_protection_case(
    owner_id: str,
    risk_score: int,
    amount: float | None,
    payee_label: str,
    payee_is_new: bool,
    signals: list[str] | None = None,
    cooling_off_minutes: int | None = None,
) -> dict:
    """Open a protection case for a payment.

    Risk tier: REVERSIBLE. A risky payment is put on hold and the first
    trusted contact is alerted automatically. Silence never releases money.
    """
    return open_protection_case_logic(
        owner_id,
        risk_score,
        amount,
        payee_label,
        payee_is_new,
        signals,
        cooling_off_minutes,
    )


@mcp.tool()
def alert_trusted_contact(case_id: str, owner_id: str) -> dict:
    """Alert the first trusted contact of a held case (safe to repeat).

    Risk tier: REVERSIBLE. A repeat call never issues a second code. The
    approval code is never part of this reply.
    """
    return alert_trusted_contact_logic(case_id, owner_id)


@mcp.tool()
def record_family_decision(
    case_id: str,
    contact_id: str,
    approval_code: str,
    decision: str,
) -> dict:
    """Record a family member's APPROVE or REJECT decision.

    Risk tier: COMMITMENT. Needs a valid one-time approval code.
    Only the family member's device may call this with the approval code.
    An AI assistant must never call it on its own.
    """
    return record_family_decision_logic(
        case_id,
        contact_id,
        approval_code,
        decision,
    )


@mcp.tool()
def get_protection_case(case_id: str, owner_id: str) -> dict:
    """Read the current state of a protection case.

    Risk tier: READ_ONLY. A wrong owner gets the same 'Case not found'
    answer as a missing case.
    """
    return get_protection_case_logic(case_id, owner_id)


@mcp.tool()
def get_case_receipt(case_id: str, owner_id: str) -> dict:
    """Return the evidence trail of a case, safe to attach to a complaint.

    Risk tier: READ_ONLY. Approval codes and secrets are never included.
    """
    return get_case_receipt_logic(case_id, owner_id)


@mcp.tool()
def get_family_inbox(case_id: str, contact_id: str) -> dict:
    """Simulated delivery channel for the family member's phone.

    Risk tier: READ_ONLY. Not for use by the assistant.
    In production this message would arrive by SMS or push, never through MCP.
    """
    return get_family_inbox_logic(case_id, contact_id)


@mcp.resource(
    "relay://shield/profile/{owner_id}",
    name="relay_shield_profile",
    title="Relay Shield Protection Profile",
    description="Protected person's payment limit and trusted contacts (no phone details).",
    mime_type="application/json",
)
def shield_profile_resource(owner_id: str) -> dict:
    profile = get_shield_profile(owner_id)

    if profile is None:
        return {"error": "Unknown protected user"}

    return {
        "owner_id": profile["owner_id"],
        "display_name": profile["display_name"],
        "payment_limit": profile["payment_limit"],
        "cooling_off_minutes": profile["cooling_off_minutes"],
        "contacts": [
            {"name": contact["name"], "order": contact["order"]}
            for contact in sorted(
                profile["contacts"],
                key=lambda item: item["order"],
            )
        ],
    }


@mcp.prompt(
    name="protect_family_from_scam",
    title="Protect a family member from a scam",
    description="Guide an agent through analyzing a message, assessing a payment and holding it for family approval.",
)
def protect_family_from_scam(owner_id: str, message: str) -> str:
    return f'''Protect this person from a possible scam with Relay Shield.

Protected user: {owner_id}
Message received: {message}

Required workflow:
1. Analyze the message with analyze_message.
2. If the message contains a phone number, check it with check_number.
3. If a payment is mentioned, assess it with assess_scam_risk.
4. If the decision is HOLD, open a protection case with open_protection_case.
   It alerts the first trusted contact by itself.
5. Explain calmly what happened and what the family was asked to do.
6. Never approve a payment, never ask for OTPs or approval codes, and never
   give legal or financial advice.'''


if __name__ == "__main__":
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts(),
        allowed_origins=[
            "http://localhost:*",
            "http://127.0.0.1:*",
        ],
    )

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=security,
    )