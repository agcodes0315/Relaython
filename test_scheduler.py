import time

from relay.audit import (
    get_task_events,
)
from relay.scheduler import (
    schedule_resume_in_minutes,
)
from relay.store import (
    save_task,
)


TEST_TASK_ID = (
    "relay-eventbridge-test"
)


def main() -> None:
    save_task(
        {
            "task_id": TEST_TASK_ID,
            "goal": (
                "Test automatic EventBridge resume"
            ),
            "budget": 2000,
            "deadline": "2026-10-10",
            "excluded_days": [],
            "status": "CREATED",
            "selected_provider": None,
            "approved": False,
        }
    )

    print(
        "Test task saved."
    )

    result = (
        schedule_resume_in_minutes(
            task_id=TEST_TASK_ID,
            minutes=2,
        )
    )

    print()
    print(
        "Schedule created:"
    )
    print(result)

    print()
    print(
        "Waiting for EventBridge Scheduler..."
    )

    for attempt in range(1, 7):
        print(
            f"Check {attempt}/6..."
        )

        time.sleep(30)

        events = get_task_events(
            TEST_TASK_ID
        )

        matching = [
            event
            for event in events
            if (
                event["event_type"]
                == "RESUME_TRIGGERED"
            )
        ]

        if matching:
            print()
            print(
                "EVENTBRIDGE RESUME TEST PASSED"
            )
            print()
            print(
                "Resume event:"
            )
            print(
                matching[-1]
            )
            return

    raise RuntimeError(
        "EventBridge did not trigger "
        "the Relay resume worker "
        "within the expected window."
    )


if __name__ == "__main__":
    main()
