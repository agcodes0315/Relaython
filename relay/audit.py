from datetime import datetime, timezone


audit_events: list[dict] = []


def record_event(
    task_id: str,
    event_type: str,
    details: dict,
) -> dict:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "event_type": event_type,
        "details": details,
    }

    audit_events.append(event)

    return event


def get_task_events(task_id: str) -> list[dict]:
    return [
        event
        for event in audit_events
        if event["task_id"] == task_id
    ]