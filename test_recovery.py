from relay.recovery import (
    restore_provider,
    simulate_provider_failure,
)
from relay.store import (
    delete_task,
    get_task,
    save_task,
)


TEST_TASK_ID = (
    "relay-failure-recovery-test"
)


def main() -> None:
    delete_task(TEST_TASK_ID)

    task = {
        "task_id": TEST_TASK_ID,
        "goal": "Test failure recovery",
        "budget": 2000,
        "deadline": "2026-10-10",
        "excluded_days": [],
        "status": "NEEDS_APPROVAL",
        "selected_provider": {
            "provider_id": "provider_1",
            "name": "CoolCare",
            "price": 1450,
            "available_date": "2026-10-09",
            "is_available": True,
        },
        "approved": False,
        "matching_providers": [
            {
                "provider_id": "provider_1",
                "name": "CoolCare",
                "price": 1450,
                "available_date": "2026-10-09",
                "is_available": True,
            },
            {
                "provider_id": "provider_2",
                "name": "QuickFix",
                "price": 1800,
                "available_date": "2026-10-07",
                "is_available": True,
            },
        ],
    }

    save_task(task)

    print(
        "Simulating provider failure..."
    )

    result = simulate_provider_failure(
        TEST_TASK_ID
    )

    print(result)

    loaded = get_task(
        TEST_TASK_ID
    )

    assert loaded is not None
    assert (
        loaded["status"]
        == "PROVIDERS_FOUND"
    )
    assert (
        loaded["selected_provider"]
        is None
    )

    assert all(
        provider["provider_id"]
        != "provider_1"
        for provider
        in loaded[
            "matching_providers"
        ]
    )

    restore_provider(
        "provider_1"
    )

    delete_task(
        TEST_TASK_ID
    )

    print()
    print(
        "FAILURE RECOVERY TEST PASSED"
    )


if __name__ == "__main__":
    main()
