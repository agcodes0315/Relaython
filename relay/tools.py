from uuid import uuid4

from relay.providers import PROVIDERS
from relay.policy import provider_is_valid
from relay.store import get_task, save_task


def create_errand_logic(
    goal: str,
    budget: float,
    deadline: str,
    excluded_days: list[str],
) -> dict:
    task_id = str(uuid4())

    task = {
        "task_id": task_id,
        "goal": goal,
        "budget": budget,
        "deadline": deadline,
        "excluded_days": excluded_days,
        "status": "CREATED",
        "selected_provider": None,
        "approved": False,
    }

    save_task(task)

    return task


def get_errand_logic(task_id: str) -> dict:
    task = get_task(task_id)

    if task is None:
        return {"error": "Task not found"}

    return task


def find_providers_logic(task_id: str) -> dict:
    task = get_task(task_id)

    if task is None:
        return {"error": "Task not found"}

    matching_providers = [
        provider
        for provider in PROVIDERS
        if provider_is_valid(
            provider,
            task["budget"],
            task["excluded_days"],
        )
    ]

    task["matching_providers"] = matching_providers
    task["status"] = "PROVIDERS_FOUND"

    save_task(task)

    return {
        "task_id": task_id,
        "status": task["status"],
        "providers": matching_providers,
    }


def propose_options_logic(task_id: str) -> dict:
    task = get_task(task_id)

    if task is None:
        return {"error": "Task not found"}

    providers = task.get("matching_providers", [])

    if not providers:
        return {
            "error": "No matching providers found. Run find_providers first."
        }

    cheapest = min(
        providers,
        key=lambda provider: provider["price"],
    )

    day_priority = {
        "Monday": 1,
        "Tuesday": 2,
        "Wednesday": 3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
        "Sunday": 7,
    }

    earliest = min(
        providers,
        key=lambda provider: day_priority.get(
            provider["available_day"],
            99,
        ),
    )

    task["status"] = "AWAITING_DECISION"
    save_task(task)

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
        ),
    }


def select_provider_logic(
    task_id: str,
    provider_id: str,
) -> dict:
    task = get_task(task_id)

    if task is None:
        return {"error": "Task not found"}

    providers = task.get("matching_providers", [])

    provider = next(
        (
            provider
            for provider in providers
            if provider["provider_id"] == provider_id
        ),
        None,
    )

    if provider is None:
        return {
            "error": "Provider is not valid for this task."
        }

    task["selected_provider"] = provider
    task["status"] = "NEEDS_APPROVAL"

    save_task(task)

    return {
        "task_id": task_id,
        "status": task["status"],
        "selected_provider": provider,
        "message": (
            f"{provider['name']} has been selected. "
            "User approval is required before booking."
        ),
    }


def approve_booking_logic(
    task_id: str,
    approve: bool,
) -> dict:
    task = get_task(task_id)

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
        save_task(task)

        return {
            "task_id": task_id,
            "status": task["status"],
            "message": "Booking was not approved.",
        }

    if provider["price"] > task["budget"]:
        task["status"] = "BLOCKED"
        save_task(task)

        return {
            "task_id": task_id,
            "status": task["status"],
            "message": (
                "Booking blocked because provider exceeds budget."
            ),
        }

    task["approved"] = True
    task["status"] = "APPROVED"

    save_task(task)

    return {
        "task_id": task_id,
        "status": task["status"],
        "provider": provider,
        "message": (
            f"Booking with {provider['name']} approved "
            f"for ₹{provider['price']}."
        ),
    }