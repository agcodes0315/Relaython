from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server import MCPServer
from mcp.server.transport_security import (
    TransportSecuritySettings,
)

from relay.recovery import (
    restore_provider as restore_provider_logic,
    simulate_provider_failure,
)
from relay.tools import (
    approve_booking_logic,
    create_errand_logic,
    find_providers_logic,
    get_audit_log_logic,
    get_errand_logic,
    propose_options_logic,
    select_provider_logic,
)


mcp = MCPServer("Relay")


@mcp.custom_route(
    "/health",
    methods=["GET"],
)
async def health(
    request: Request,
) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": "relay-mcp",
        }
    )


@mcp.tool()
def create_errand(
    goal: str,
    budget: float,
    deadline: str,
    excluded_days: list[str],
) -> dict:
    return create_errand_logic(
        goal,
        budget,
        deadline,
        excluded_days,
    )


@mcp.tool()
def get_errand(
    task_id: str,
) -> dict:
    return get_errand_logic(
        task_id
    )


@mcp.tool()
def find_providers(
    task_id: str,
) -> dict:
    return find_providers_logic(
        task_id
    )


@mcp.tool()
def propose_options(
    task_id: str,
) -> dict:
    return propose_options_logic(
        task_id
    )


@mcp.tool()
def select_provider(
    task_id: str,
    provider_id: str,
) -> dict:
    return select_provider_logic(
        task_id,
        provider_id,
    )


@mcp.tool()
def approve_booking(
    task_id: str,
    approve: bool,
) -> dict:
    return approve_booking_logic(
        task_id,
        approve,
    )


@mcp.tool()
def get_audit_log(
    task_id: str,
) -> list[dict]:
    return get_audit_log_logic(
        task_id
    )


@mcp.tool()
def simulate_provider_failure_tool(
    task_id: str,
) -> dict:
    """
    Simulate the selected provider becoming
    unavailable after selection or approval.

    Relay invalidates the previous approval,
    reapplies the original constraints, and
    returns the task to provider selection.
    """
    return simulate_provider_failure(
        task_id
    )


@mcp.tool()
def restore_provider(
    provider_id: str,
) -> dict:
    """
    Restore a simulated provider so the
    demo can be run repeatedly.
    """
    return restore_provider_logic(
        provider_id
    )


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=(
            TransportSecuritySettings(
                enable_dns_rebinding_protection=False,
            )
        ),
    )