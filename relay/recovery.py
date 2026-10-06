from relay.audit import record_event
from relay.providers import (
    get_providers,
    mark_provider_available,
    mark_provider_unavailable,
)
from relay.store import get_task, save_task


def simulate_provider_failure(
    task_id: str,
) -> dict:
    task = get_task(task_id)

    if task is None:
        return {
            "error": "Task not found"
        }

    selected_provider = task.get(
        "selected_provider"
    )

    if selected_provider is None:
        return {
            "error": (
                "No selected provider exists "
                "for this task."
            )
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
            "error": "Provider not found"
        }

    record_event(
        task_id,
        "PROVIDER_FAILED",
        {
            "provider_id": provider_id,
            "provider_name": (
                selected_provider["name"]
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
            provider["provider_id"]
            != provider_id
            and provider.get(
                "is_available",
                True,
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
                provider["provider_id"]
                for provider in remaining
            ],
        },
    )

    return {
        "task_id": task_id,
        "status": task["status"],
        "failed_provider": (
            failed_provider
        ),
        "remaining_providers": (
            remaining
        ),
        "message": (
            "Selected provider became "
            "unavailable. Relay recovered "
            "the task and returned it to "
            "provider selection."
        ),
    }


def restore_provider(
    provider_id: str,
) -> dict:
    provider = mark_provider_available(
        provider_id
    )

    if provider is None:
        return {
            "error": "Provider not found"
        }

    return provider
