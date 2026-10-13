import json
from datetime import datetime, timedelta, timezone
import relay.scheduler as scheduler_module
class FakeNotFound(Exception):
    pass
class FakeScheduler:
    class exceptions:
        ResourceNotFoundException = FakeNotFound
    def __init__(self):
        self.created = []
        self.deleted = []
        self.raise_not_found = True

    def delete_schedule(self, **kwargs):
        self.deleted.append(kwargs)

        if self.raise_not_found:
            raise FakeNotFound()

    def create_schedule(self, **kwargs):
        self.created.append(kwargs)

        return {
            "ScheduleArn": (
                "arn:aws:scheduler:"
                "us-west-2:123:"
                "schedule/default/test"
            )
        }

class FakeIAM:
    def get_role(self, **kwargs):
        return {
            "Role": {
                "Arn": "arn:aws:iam::123:role/test"
            }
        }

class FakeLambda:
    def get_function(self, **kwargs):
        return {
            "Configuration": {
                "FunctionArn": (
                    "arn:aws:lambda:"
                    "us-west-2:123:"
                    "function:test"
                )
            }
        }

def setup_scheduler(monkeypatch):
    fake_scheduler = FakeScheduler()

    monkeypatch.setattr(
        scheduler_module,
        "scheduler",
        fake_scheduler,
    )

    monkeypatch.setattr(
        scheduler_module,
        "iam",
        FakeIAM(),
    )

    monkeypatch.setattr(
        scheduler_module,
        "lambda_client",
        FakeLambda(),
    )

    return fake_scheduler


def future_time():
    return (
        datetime.now(timezone.utc)
        + timedelta(minutes=10)
    )


def test_default_schedule_preserves_old_behavior(
    monkeypatch,
):
    fake_scheduler = setup_scheduler(
        monkeypatch
    )

    task = {
        "task_id": "task-123",
        "status": "CREATED",
    }

    saved = []
    events = []

    monkeypatch.setattr(
        scheduler_module,
        "get_task",
        lambda task_id: task.copy(),
    )

    monkeypatch.setattr(
        scheduler_module,
        "save_task",
        lambda value: saved.append(value),
    )

    monkeypatch.setattr(
        scheduler_module,
        "record_event",
        lambda *args: events.append(args),
    )

    result = (
        scheduler_module.schedule_resume(
            "task-123",
            future_time(),
        )
    )

    assert (
        result["schedule_name"]
        == "relay-resume-task-123"
    )

    assert len(
        fake_scheduler.created
    ) == 1

    payload = json.loads(
        fake_scheduler.created[0][
            "Target"
        ]["Input"]
    )

    assert payload == {
        "task_id": "task-123",
        "source": "relay-mcp-scheduler",
    }

    assert len(saved) == 1

    assert (
        saved[0]["wait_status"]
        == "SCHEDULED"
    )

    assert (
        saved[0]["wait_schedule_name"]
        == "relay-resume-task-123"
    )

    assert (
        "wait_scheduled_for"
        in saved[0]
    )

    assert len(events) == 1

    assert events[0][1] == (
        "WAIT_SCHEDULED"
    )


def test_suffix_creates_independent_timer(
    monkeypatch,
):
    setup_scheduler(monkeypatch)

    monkeypatch.setattr(
        scheduler_module,
        "get_task",
        lambda task_id: {
            "task_id": task_id
        },
    )

    monkeypatch.setattr(
        scheduler_module,
        "save_task",
        lambda task: None,
    )

    monkeypatch.setattr(
        scheduler_module,
        "record_event",
        lambda *args: None,
    )

    first = (
        scheduler_module.schedule_resume(
            "x" * 60,
            future_time(),
            name_suffix="e1",
        )
    )

    second = (
        scheduler_module.schedule_resume(
            "x" * 60,
            future_time(),
            name_suffix="expire",
        )
    )

    assert (
        first["schedule_name"]
        != second["schedule_name"]
    )

    assert (
        first["schedule_name"]
        .endswith("-e1")
    )

    assert (
        second["schedule_name"]
        .endswith("-expire")
    )

    assert len(
        first["schedule_name"]
    ) <= 64

    assert len(
        second["schedule_name"]
    ) <= 64
def test_extra_payload_is_merged_but_task_id_wins(
    monkeypatch,
):
    fake_scheduler = setup_scheduler(
        monkeypatch
    )
    monkeypatch.setattr(
        scheduler_module,
        "get_task",
        lambda task_id: {
            "task_id": task_id
        },
    )
    monkeypatch.setattr(
        scheduler_module,
        "save_task",
        lambda task: None,
    )
    monkeypatch.setattr(
        scheduler_module,
        "record_event",
        lambda *args: None,
    )
    scheduler_module.schedule_resume(
        "real-task",
        future_time(),
        extra_payload={
            "step": "ESCALATE",
            "to_index": 1,
            "task_id": "wrong-task",
        },
    )
    payload = json.loads(
        fake_scheduler.created[0][
            "Target"
        ]["Input"]
    )

    assert (
        payload["task_id"]
        == "real-task"
    )

    assert (
        payload["source"]
        == "relay-mcp-scheduler"
    )

    assert (
        payload["step"]
        == "ESCALATE"
    )

    assert payload["to_index"] == 1
def test_persist_false_does_not_modify_task(
    monkeypatch,
):
    setup_scheduler(monkeypatch)

    original = {
        "task_id": "case-123",
        "status": "AWAITING_FAMILY",
    }

    saved = []
    events = []

    monkeypatch.setattr(
        scheduler_module,
        "get_task",
        lambda task_id: original.copy(),
    )

    monkeypatch.setattr(
        scheduler_module,
        "save_task",
        lambda task: saved.append(task),
    )

    monkeypatch.setattr(
        scheduler_module,
        "record_event",
        lambda *args: events.append(args),
    )

    result = (
        scheduler_module.schedule_resume(
            "case-123",
            future_time(),
            name_suffix="e1",
            extra_payload={
                "step": "ESCALATE",
                "to_index": 1,
            },
            persist_task=False,
        )
    )

    assert result[
        "wait_status"
    ] == "SCHEDULED"

    assert saved == []
    assert events == []

    assert (
        "wait_status"
        not in original
    )
def test_unknown_task_creates_nothing(
    monkeypatch,
):
    fake_scheduler = setup_scheduler(
        monkeypatch
    )
    monkeypatch.setattr(
        scheduler_module,
        "get_task",
        lambda task_id: None,
    )
    result = (
        scheduler_module.schedule_resume(
            "missing",
            future_time(),
        )
    )
    assert result == {
        "error": "Task not found"
    }
    assert (
        fake_scheduler.created
        == []
    )
def test_past_time_creates_nothing(
    monkeypatch,
):
    fake_scheduler = setup_scheduler(
        monkeypatch
    )

    monkeypatch.setattr(
        scheduler_module,
        "get_task",
        lambda task_id: {
            "task_id": task_id
        },
    )

    result = (
        scheduler_module.schedule_resume(
            "task-123",
            datetime.now(
                timezone.utc
            )
            - timedelta(minutes=1),
        )
    )

    assert (
        result["error"]
        == "Resume time must be in the future."
    )

    assert (
        fake_scheduler.created
        == []
    )
def test_delete_existing_schedule_returns_true(
    monkeypatch,
):
    fake_scheduler = setup_scheduler(
        monkeypatch
    )

    fake_scheduler.raise_not_found = False
    assert (
        scheduler_module
        .delete_resume_schedule(
            "case-123",
            "e1",
        )
        is True
    )
def test_delete_missing_schedule_returns_false(
    monkeypatch,
):
    setup_scheduler(monkeypatch)

    assert (
        scheduler_module
        .delete_resume_schedule(
            "case-123",
            "e1",
        )
        is False
    )
def test_existing_minute_bounds_remain(
    monkeypatch,
):
    zero = (
        scheduler_module
        .schedule_resume_in_minutes(
            "task",
            0,
        )
    )
    sixty_one = (
        scheduler_module
        .schedule_resume_in_minutes(
            "task",
            61,
        )
    )
    assert (
        zero["error"]
        == "minutes must be at least 1"
    )
    assert (
        sixty_one["error"]
        == (
            "Demo resume delay "
            "cannot exceed 60 minutes."
        )
    )