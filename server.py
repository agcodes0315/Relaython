from mcp.server import MCPServer

from relay.tools import (
    approve_booking_logic,
    create_errand_logic,
    find_providers_logic,
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
    return create_errand_logic(
        goal,
        budget,
        deadline,
        excluded_days,
    )


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


if __name__ == "__main__":
    mcp.run()