from uuid import uuid4

from relay.audit import get_task_events, record_event
from relay.policy import (
    evaluate_action,
    provider_is_valid,
    validate_transition,
)
from relay.providers import get_providers
from relay.store import get_task, save_task


def _transition_task(
    task: dict,
    next_status: str,
) -> dict | None:
    valid, reason = validate_transition(
        task["status"],
        next_status,
    )

    if not valid:
        return {
            "error": reason,
            "current_status": task["status"],
            "requested_status": next_status,
        }

    task["status"] = next_status
    save_task(task)

    return None


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

    record_event(
        task_id,
        "TASK_CREATED",
        {
            "goal": goal,
            "budget": budget,
            "deadline": deadline,
            "excluded_days": excluded_days,
        },
    )

    return task


def get_errand_logic(
    task_id: str,
) -> dict:
    task = get_task(task_id)

    if task is None:
        return {
            "error": "Task not found"
        }

    return task


def find_providers_logic(
    task_id: str,
) -> dict:
    task = get_task(task_id)

    if task is None:
        return {
            "error": "Task not found"
        }

    if task["status"] != "CREATED":
        return {
            "error": (
                "find_providers can only run when "
                "the task status is CREATED."
            ),
            "current_status": task["status"],
        }

    policy_result = evaluate_action(
        action="SEARCH_PROVIDERS",
    )

    record_event(
        task_id,
        "POLICY_EVALUATED",
        {
            "action": "SEARCH_PROVIDERS",
            **policy_result,
        },
    )

    if policy_result["decision"] == "BLOCK":
        transition_error = _transition_task(
            task,
            "BLOCKED",
        )

        if transition_error:
            return transition_error

        record_event(
            task_id,
            "SEARCH_BLOCKED",
            {
                "reason": (
                    policy_result["reason"]
                ),
            },
        )

        return {
            "task_id": task_id,
            "status": task["status"],
            "policy": policy_result,
            "message": (
                policy_result["reason"]
            ),
        }

    providers = get_providers()

    matching_providers = []
    rejected_providers = []

    for provider in providers:
        if provider_is_valid(
            provider=provider,
            budget=task["budget"],
            excluded_days=task[
                "excluded_days"
            ],
            deadline=task["deadline"],
        ):
            matching_providers.append(
                provider
            )
        else:
            rejected_providers.append(
                provider
            )

    task["matching_providers"] = (
        matching_providers
    )

    next_status = (
        "PROVIDERS_FOUND"
        if matching_providers
        else "NO_PROVIDERS"
    )

    transition_error = _transition_task(
        task,
        next_status,
    )

    if transition_error:
        return transition_error

    record_event(
        task_id,
        "PROVIDERS_FILTERED",
        {
            "matching_provider_ids": [
                provider["provider_id"]
                for provider
                in matching_providers
            ],
            "rejected_provider_ids": [
                provider["provider_id"]
                for provider
                in rejected_providers
            ],
            "deadline": task["deadline"],
            "excluded_days": (
                task["excluded_days"]
            ),
            "budget": task["budget"],
        },
    )

    return {
        "task_id": task_id,
        "status": task["status"],
        "providers": matching_providers,
    }


def propose_options_logic(
    task_id: str,
) -> dict:
    task = get_task(task_id)

    if task is None:
        return {
            "error": "Task not found"
        }

    if task["status"] != "PROVIDERS_FOUND":
        return {
            "error": (
                "propose_options can only run "
                "after providers have been found."
            ),
            "current_status": task["status"],
        }

    providers = task.get(
        "matching_providers",
        [],
    )

    if not providers:
        return {
            "error": (
                "No matching providers exist "
                "for this task."
            )
        }

    cheapest = min(
        providers,
        key=lambda provider: provider["price"],
    )

    earliest = min(
        providers,
        key=lambda provider: (
            provider["available_date"]
        ),
    )

    transition_error = _transition_task(
        task,
        "AWAITING_DECISION",
    )

    if transition_error:
        return transition_error

    record_event(
        task_id,
        "OPTIONS_PROPOSED",
        {
            "cheapest_provider_id": (
                cheapest["provider_id"]
            ),
            "earliest_provider_id": (
                earliest["provider_id"]
            ),
        },
    )

    return {
        "task_id": task_id,
        "status": task["status"],
        "cheapest_option": cheapest,
        "earliest_option": earliest,
        "providers": providers,
        "message": (
            f"I found {len(providers)} valid "
            f"providers. "
            f"{cheapest['name']} is cheapest "
            f"at ₹{cheapest['price']} on "
            f"{cheapest['available_date']} "
            f"({cheapest['available_day']}). "
            f"{earliest['name']} is earliest "
            f"at ₹{earliest['price']} on "
            f"{earliest['available_date']} "
            f"({earliest['available_day']})."
        ),
    }


def select_provider_logic(
    task_id: str,
    provider_id: str,
) -> dict:
    task = get_task(task_id)

    if task is None:
        return {
            "error": "Task not found"
        }

    if task["status"] != "AWAITING_DECISION":
        return {
            "error": (
                "select_provider can only run "
                "when the task is awaiting "
                "a user decision."
            ),
            "current_status": task["status"],
        }

    providers = task.get(
        "matching_providers",
        [],
    )

    provider = next(
        (
            provider
            for provider in providers
            if (
                provider["provider_id"]
                == provider_id
            )
        ),
        None,
    )

    if provider is None:
        return {
            "error": (
                "Provider is not valid "
                "for this task."
            )
        }

    policy_result = evaluate_action(
        action="SELECT_PROVIDER",
    )

    record_event(
        task_id,
        "POLICY_EVALUATED",
        {
            "action": "SELECT_PROVIDER",
            **policy_result,
        },
    )

    if policy_result["decision"] == "BLOCK":
        transition_error = _transition_task(
            task,
            "BLOCKED",
        )

        if transition_error:
            return transition_error

        return {
            "task_id": task_id,
            "status": task["status"],
            "policy": policy_result,
        }

    task["selected_provider"] = provider

    transition_error = _transition_task(
        task,
        "NEEDS_APPROVAL",
    )

    if transition_error:
        return transition_error

    record_event(
        task_id,
        "PROVIDER_SELECTED",
        {
            "provider_id": (
                provider["provider_id"]
            ),
            "provider_name": (
                provider["name"]
            ),
            "price": provider["price"],
            "available_date": (
                provider["available_date"]
            ),
        },
    )

    return {
        "task_id": task_id,
        "status": task["status"],
        "selected_provider": provider,
        "message": (
            f"{provider['name']} has been "
            f"selected for "
            f"{provider['available_date']} "
            f"({provider['available_day']}). "
            f"Explicit user approval is "
            f"required before booking."
        ),
    }


def approve_booking_logic(
    task_id: str,
    approve: bool,
) -> dict:
    task = get_task(task_id)

    if task is None:
        return {
            "error": "Task not found"
        }

    if task["status"] != "NEEDS_APPROVAL":
        return {
            "error": (
                "approve_booking can only run "
                "when explicit approval is "
                "required."
            ),
            "current_status": task["status"],
        }

    provider = task.get(
        "selected_provider"
    )

    if provider is None:
        return {
            "error": (
                "No provider has been selected."
            )
        }

    policy_result = evaluate_action(
        action="BOOK_PROVIDER",
        amount=provider["price"],
        max_budget=task["budget"],
    )

    record_event(
        task_id,
        "POLICY_EVALUATED",
        {
            "action": "BOOK_PROVIDER",
            **policy_result,
        },
    )

    if policy_result["decision"] == "BLOCK":
        task["approved"] = False

        transition_error = _transition_task(
            task,
            "BLOCKED",
        )

        if transition_error:
            return transition_error

        record_event(
            task_id,
            "BOOKING_BLOCKED",
            {
                "provider_id": (
                    provider["provider_id"]
                ),
                "reason": (
                    policy_result["reason"]
                ),
            },
        )

        return {
            "task_id": task_id,
            "status": task["status"],
            "policy": policy_result,
            "message": (
                policy_result["reason"]
            ),
        }

    if not approve:
        task["approved"] = False

        transition_error = _transition_task(
            task,
            "REJECTED",
        )

        if transition_error:
            return transition_error

        record_event(
            task_id,
            "USER_REJECTED",
            {
                "provider_id": (
                    provider["provider_id"]
                ),
                "amount": (
                    provider["price"]
                ),
            },
        )

        return {
            "task_id": task_id,
            "status": task["status"],
            "policy": policy_result,
            "message": (
                "Booking was not approved."
            ),
        }

    task["approved"] = True

    transition_error = _transition_task(
        task,
        "APPROVED",
    )

    if transition_error:
        return transition_error

    record_event(
        task_id,
        "USER_APPROVED",
        {
            "provider_id": (
                provider["provider_id"]
            ),
            "provider_name": (
                provider["name"]
            ),
            "amount": provider["price"],
            "available_date": (
                provider["available_date"]
            ),
        },
    )

    return {
        "task_id": task_id,
        "status": task["status"],
        "provider": provider,
        "policy": policy_result,
        "message": (
            f"Booking with "
            f"{provider['name']} approved "
            f"for ₹{provider['price']} on "
            f"{provider['available_date']}."
        ),
    }


def get_audit_log_logic(
    task_id: str,
) -> list[dict]:
    return get_task_events(
        task_id
    )
