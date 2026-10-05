from uuid import uuid4
from mcp.server import MCPServer

mcp = MCPServer("Relay")

tasks = {}

PROVIDERS = [
    {
        "provider_id": "provider_1",
        "name": "CoolCare",
        "price": 1450,
        "available_day": "Friday"
    },
    {
        "provider_id": "provider_2",
        "name": "QuickFix",
        "price": 1800,
        "available_day": "Wednesday"
    },
    {
        "provider_id": "provider_3",
        "name": "PremiumAir",
        "price": 2600,
        "available_day": "Tuesday"
    }
]


@mcp.tool()
def create_errand(
    goal: str,
    budget: float,
    deadline: str,
    excluded_days: list[str]
) -> dict:
    """
    Create a new Relay errand with user-defined constraints.
    """

    task_id = str(uuid4())

    task = {
        "task_id": task_id,
        "goal": goal,
        "budget": budget,
        "deadline": deadline,
        "excluded_days": excluded_days,
        "status": "CREATED",
        "selected_provider": None,
        "approved": False
    }

    tasks[task_id] = task

    return task


@mcp.tool()
def get_errand(task_id: str) -> dict:
    """
    Retrieve an existing Relay errand.
    """

    task = tasks.get(task_id)

    if task is None:
        return {"error": "Task not found"}

    return task


@mcp.tool()
def find_providers(task_id: str) -> dict:
    """
    Find providers that satisfy the errand's hard constraints.
    """

    task = tasks.get(task_id)

    if task is None:
        return {"error": "Task not found"}

    matching_providers = []

    for provider in PROVIDERS:
        within_budget = provider["price"] <= task["budget"]
        allowed_day = provider["available_day"] not in task["excluded_days"]

        if within_budget and allowed_day:
            matching_providers.append(provider)

    task["status"] = "PROVIDERS_FOUND"
    task["matching_providers"] = matching_providers

    return {
        "task_id": task_id,
        "status": task["status"],
        "providers": matching_providers
    }


@mcp.tool()
def propose_options(task_id: str) -> dict:
    """
    Compare valid providers and produce cheaper and earlier recommendations.
    """

    task = tasks.get(task_id)

    if task is None:
        return {"error": "Task not found"}

    providers = task.get("matching_providers", [])

    if not providers:
        return {
            "error": "No matching providers found. Run find_providers first."
        }

    cheapest = min(providers, key=lambda p: p["price"])

    day_priority = {
        "Monday": 1,
        "Tuesday": 2,
        "Wednesday": 3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
        "Sunday": 7
    }

    earliest = min(
        providers,
        key=lambda p: day_priority.get(p["available_day"], 99)
    )

    task["status"] = "AWAITING_DECISION"

    return {
        "task_id": task_id,
        "status": task["status"],
        "cheapest_option": cheapest,
        "earliest_option": earliest,
        "message": (
            f"I found {len(providers)} valid providers. "
            f"{cheapest['name']} is cheapest at ₹{cheapest['price']} "
            f"on {cheapest['available_day']}. "
            f"{earliest['name']} is earliest at ₹{earliest['price']} "
            f"on {earliest['available_day']}."
        )
    }


@mcp.tool()
def select_provider(task_id: str, provider_id: str) -> dict:
    """
    Select one of the valid providers for the errand.
    """

    task = tasks.get(task_id)

    if task is None:
        return {"error": "Task not found"}

    providers = task.get("matching_providers", [])

    provider = next(
        (p for p in providers if p["provider_id"] == provider_id),
        None
    )

    if provider is None:
        return {
            "error": "Provider is not valid for this task."
        }

    task["selected_provider"] = provider
    task["status"] = "NEEDS_APPROVAL"

    return {
        "task_id": task_id,
        "status": task["status"],
        "selected_provider": provider,
        "message": (
            f"{provider['name']} has been selected. "
            "User approval is required before booking."
        )
    }


@mcp.tool()
def approve_booking(task_id: str, approve: bool) -> dict:
    """
    Approve or reject the selected provider booking.
    """

    task = tasks.get(task_id)

    if task is None:
        return {"error": "Task not found"}

    provider = task.get("selected_provider")

    if provider is None:
        return {
            "error": "No provider has been selected."
        }

    if not approve:
        task["status"] = "REJECTED"
        task["approved"] = False

        return {
            "task_id": task_id,
            "status": task["status"],
            "message": "Booking was not approved."
        }

    if provider["price"] > task["budget"]:
        task["status"] = "BLOCKED"

        return {
            "task_id": task_id,
            "status": task["status"],
            "message": "Booking blocked because provider exceeds budget."
        }

    task["approved"] = True
    task["status"] = "APPROVED"

    return {
        "task_id": task_id,
        "status": task["status"],
        "provider": provider,
        "message": (
            f"Booking with {provider['name']} approved "
            f"for ₹{provider['price']}."
        )
    }


if __name__ == "__main__":
    mcp.run()