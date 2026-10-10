from datetime import date

from relay.idempotency import InMemoryIdempotencyStore, execute_idempotently
from relay.provider_adapter import ProviderOption, TaskConstraints, compliant_options
from relay.resume_retry import RetryPolicy, run_with_bounded_retry
from relay.decision_receipt import build_decision_receipt


def test_duplicate_approval_executes_once():
    store = InMemoryIdempotencyStore()
    calls = {"count": 0}

    def do_work():
        calls["count"] += 1
        return {"approved": True}

    first = execute_idempotently(
        operation="approve_booking",
        task_id="task-1",
        payload={"provider_id": "quickfix"},
        store=store,
        fn=do_work,
    )
    second = execute_idempotently(
        operation="approve_booking",
        task_id="task-1",
        payload={"provider_id": "quickfix"},
        store=store,
        fn=do_work,
    )

    assert first.duplicate is False
    assert second.duplicate is True
    assert calls["count"] == 1


def test_recovery_reapplies_original_constraints():
    constraints = TaskConstraints(
        max_budget=2000,
        deadline=date(2026, 10, 10),
        excluded_weekdays=frozenset({"Thursday"}),
    )

    options = [
        ProviderOption("coolcare", "CoolCare", 1450, date(2026, 10, 9)),
        ProviderOption("premiumair", "PremiumAir", 2600, date(2026, 10, 6)),
        ProviderOption("thursday", "ThursdayCo", 1500, date(2026, 10, 8)),
        ProviderOption("late", "LateCo", 1200, date(2026, 10, 12)),
    ]

    assert [x.provider_id for x in compliant_options(options, constraints)] == ["coolcare"]


def test_resume_retry_is_bounded():
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("temporary")
        return "ok"

    result = run_with_bounded_retry(
        flaky,
        policy=RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0,
            multiplier=1,
            max_delay_seconds=0,
        ),
        retryable=lambda exc: isinstance(exc, TimeoutError),
        sleep=lambda _: None,
    )

    assert result == "ok"
    assert calls["count"] == 3


def test_decision_receipt_orders_events():
    receipt = build_decision_receipt([
        {"event_type": "TASK_RESUMED", "timestamp": "2026-10-10T10:02:00+00:00"},
        {"event_type": "WAIT_SCHEDULED", "timestamp": "2026-10-10T10:00:00+00:00"},
    ])

    assert receipt["events"][0]["event_type"] == "WAIT_SCHEDULED"
    assert receipt["events"][1]["event_type"] == "TASK_RESUMED"
