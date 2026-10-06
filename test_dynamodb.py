from relay.audit import (
    delete_task_events,
    get_task_events,
    record_event,
)
from relay.store import (
    delete_task,
    get_task,
    save_task,
)


TEST_TASK_ID = (
    "relay-dynamodb-test-task"
)


def cleanup() -> None:
    delete_task_events(
        TEST_TASK_ID
    )

    delete_task(
        TEST_TASK_ID
    )


def main() -> None:
    cleanup()

    print(
        "1. Saving task to DynamoDB..."
    )

    task = {
        "task_id": TEST_TASK_ID,
        "goal": (
            "Test persistent Relay task"
        ),
        "budget": 2000,
        "deadline": "2026-10-10",
        "excluded_days": [
            "Thursday"
        ],
        "status": "CREATED",
        "selected_provider": None,
        "approved": False,
    }

    save_task(task)

    print(
        "2. Reading task from DynamoDB..."
    )

    loaded_task = get_task(
        TEST_TASK_ID
    )

    assert loaded_task is not None
    assert (
        loaded_task["task_id"]
        == TEST_TASK_ID
    )
    assert (
        loaded_task["budget"]
        == 2000
    )

    print(
        "3. Writing audit event..."
    )

    record_event(
        TEST_TASK_ID,
        "TEST_EVENT",
        {
            "message": (
                "DynamoDB persistence works"
            )
        },
    )

    print(
        "4. Reading audit events..."
    )

    events = get_task_events(
        TEST_TASK_ID
    )

    assert len(events) >= 1
    assert (
        events[-1]["event_type"]
        == "TEST_EVENT"
    )

    print()
    print(
        "DynamoDB persistence test PASSED"
    )

    print()
    print(
        "Stored task:"
    )
    print(
        loaded_task
    )

    print()
    print(
        "Audit events:"
    )

    for event in events:
        print(event)

    cleanup()

    print()
    print(
        "Test data cleaned up."
    )


if __name__ == "__main__":
    main()
