from datetime import date

from relay.audit import record_event
from relay.providers import (
    get_providers,
    mark_provider_available,
    mark_provider_unavailable,
)
from relay.store import get_task, save_task


def _provider_matches_constraints(
    provider: dict,
    task: dict,
) -> bool:
    """
    Reapply the original delegation contract
    when Relay recovers from a provider failure.

    A replacement provider must still satisfy:
    - provider availability
    - budget
    - deadline
    - excluded weekdays
    """

    if not provider.get(
        "is_available",
        True,
    ):
        return False

    budget = task.get("budget")

    if budget is not None:
        provider_price = provider.get(
            "price"
        )

        if (
            provider_price is None
            or provider_price > budget
        ):
            return False

    deadline = task.get("deadline")

    available_date = provider.get(
        "available_date"
    )

    if deadline and available_date:
        provider_date = (
            date.fromisoformat(
                available_date
            )
        )

        deadline_date = (
            date.fromisoformat(
                deadline
            )
        )

        if provider_date > deadline_date:
            return False

    excluded_days = {
        str(day).strip().lower()
        for day in task.get(
            "excluded_days",
            [],
        )
    }

    if available_date:
        provider_weekday = (
            date.fromisoformat(
                available_date
            )
            .strftime("%A")
            .lower()
        )

        if (
            provider_weekday
            in excluded_days
        ):
            return False

    return True


def simulate_provider_failure(
    task_id: str,
) -> dict:
    task = get_task(task_id)

    if task is None:
        return {
            "error": "Task not found",
        }

    selected_provider = task.get(
        "selected_provider"
    )

    if selected_provider is None:
        return {
            "error": (
                "No selected provider exists "
                "for this task."
            ),
        }

    provider_id = selected_provider[
        "provider_id"
    ]

    failed_provider = (
        mark_provider_unavailable(
            provider_id
        )
    )

    if failed_provider is None:
        return {
            "error": "Provider not found",
        }

    record_event(
        task_id,
        "PROVIDER_FAILED",
        {
            "provider_id": provider_id,
            "provider_name": (
                selected_provider[
                    "name"
                ]
            ),
            "reason": (
                "Simulated provider "
                "cancellation/unavailability"
            ),
        },
    )

    remaining = [
        provider
        for provider in get_providers()
        if (
            provider[
                "provider_id"
            ]
            != provider_id
            and _provider_matches_constraints(
                provider,
                task,
            )
        )
    ]

    task[
        "selected_provider"
    ] = None

    task[
        "approved"
    ] = False

    task[
        "matching_providers"
    ] = remaining

    task[
        "status"
    ] = (
        "PROVIDERS_FOUND"
        if remaining
        else "NO_PROVIDERS"
    )

    save_task(task)

    record_event(
        task_id,
        "RECOVERY_STARTED",
        {
            "previous_provider_id": (
                provider_id
            ),
            "remaining_provider_ids": [
                provider[
                    "provider_id"
                ]
                for provider
                in remaining
            ],
            "constraints_reapplied": True,
            "budget": task.get(
                "budget"
            ),
            "deadline": task.get(
                "deadline"
            ),
            "excluded_days": (
                task.get(
                    "excluded_days",
                    [],
                )
            ),
        },
    )

    return {
        "task_id": task_id,
        "status": task[
            "status"
        ],
        "failed_provider": (
            failed_provider
        ),
        "remaining_providers": (
            remaining
        ),
        "approval_reset": True,
        "constraints_reapplied": True,
        "message": (
            "Selected provider became "
            "unavailable. Relay invalidated "
            "the previous approval, reapplied "
            "the original delegation contract, "
            "and returned the task to provider "
            "selection."
        ),
    }


def restore_provider(
    provider_id: str,
) -> dict:
    provider = (
        mark_provider_available(
            provider_id
        )
    )

    if provider is None:
        return {
            "error": "Provider not found",
        }

    return provider