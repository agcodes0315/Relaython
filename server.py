from mcp.server import MCPServer

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


@mcp.tool()
def create_errand(
    goal: str,
    budget: float,
    deadline: str,
    excluded_days: list[str],
) -> dict:
    """
    Create a new Relay errand with user-defined constraints.
    """
    return create_errand_logic(
        goal,
        budget,
        deadline,
        excluded_days,
    )


@mcp.tool()
def get_errand(task_id: str) -> dict:
    """
    Retrieve an existing Relay errand.
    """
    return get_errand_logic(task_id)


@mcp.tool()
def find_providers(task_id: str) -> dict:
    """
    Find service providers that satisfy the user's constraints.
    """
    return find_providers_logic(task_id)


@mcp.tool()
def propose_options(task_id: str) -> dict:
    """
    Compare valid providers and propose useful choices.
    """
    return propose_options_logic(task_id)


@mcp.tool()
def select_provider(
    task_id: str,
    provider_id: str,
) -> dict:
    """
    Select one valid provider for the errand.
    """
    return select_provider_logic(
        task_id,
        provider_id,
    )


@mcp.tool()
def approve_booking(
    task_id: str,
    approve: bool,
) -> dict:
    """
    Approve or reject the selected provider booking.
    """
    return approve_booking_logic(
        task_id,
        approve,
    )


@mcp.tool()
def get_audit_log(task_id: str) -> list[dict]:
    """
    Retrieve the full audit trail for an errand.
    """
    return get_audit_log_logic(task_id)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )