import json
import os
from datetime import datetime, timedelta, timezone

import boto3

from relay.audit import record_event
from relay.store import get_task, save_task


AWS_REGION = os.environ.get(
    "AWS_REGION",
    "us-west-2",
)

SCHEDULER_ROLE_NAME = os.environ.get(
    "RELAY_SCHEDULER_ROLE",
    "RelaySchedulerInvokeRole",
)

LAMBDA_FUNCTION_NAME = os.environ.get(
    "RELAY_RESUME_LAMBDA",
    "RelayResumeWorker",
)


scheduler = boto3.client(
    "scheduler",
    region_name=AWS_REGION,
)

iam = boto3.client(
    "iam",
)

lambda_client = boto3.client(
    "lambda",
    region_name=AWS_REGION,
)


def _schedule_name(
    task_id: str,
    name_suffix: str = "",
) -> str:
    prefix = "relay-resume-"

    safe_id = (
        str(task_id)
        .replace("_", "-")
        .replace(":", "-")
    )

    suffix = (
        str(name_suffix)
        .replace("_", "-")
        .replace(":", "-")
    )

    suffix_part = f"-{suffix}" if suffix else ""

    available_for_id = (
        64
        - len(prefix)
        - len(suffix_part)
    )

    if available_for_id < 0:
        available_for_id = 0

    safe_id = safe_id[:available_for_id]

    name = (
        prefix
        + safe_id
        + suffix_part
    )

    return name[:64]


def delete_resume_schedule(
    task_id: str,
    name_suffix: str = "",
) -> bool:
    name = _schedule_name(
        task_id,
        name_suffix,
    )

    try:
        scheduler.delete_schedule(
            Name=name,
        )

        return True

    except (
        scheduler.exceptions
        .ResourceNotFoundException
    ):
        return False


def schedule_resume(
    task_id: str,
    run_at: datetime,
    *,
    name_suffix: str = "",
    extra_payload: dict | None = None,
    persist_task: bool = True,
) -> dict:
    task = get_task(task_id)

    if task is None:
        return {
            "error": "Task not found",
        }

    if run_at.tzinfo is None:
        run_at = run_at.replace(
            tzinfo=timezone.utc,
        )

    run_at_utc = run_at.astimezone(
        timezone.utc,
    )

    now = datetime.now(
        timezone.utc,
    )

    if run_at_utc <= now:
        return {
            "error": (
                "Resume time must be "
                "in the future."
            )
        }

    role_arn = iam.get_role(
        RoleName=SCHEDULER_ROLE_NAME,
    )["Role"]["Arn"]

    lambda_arn = (
        lambda_client.get_function(
            FunctionName=(
                LAMBDA_FUNCTION_NAME
            )
        )["Configuration"][
            "FunctionArn"
        ]
    )

    expression = (
        "at("
        + run_at_utc.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        + ")"
    )

    name = _schedule_name(
        task_id,
        name_suffix,
    )

    payload_data = {}

    if extra_payload:
        payload_data.update(
            extra_payload
        )

    # Core Relay fields always win so callers
    # cannot redirect a timer to another task.
    payload_data["task_id"] = task_id
    payload_data["source"] = (
        "relay-mcp-scheduler"
    )

    payload = json.dumps(
        payload_data
    )

    try:
        scheduler.delete_schedule(
            Name=name,
        )

    except (
        scheduler.exceptions
        .ResourceNotFoundException
    ):
        pass

    response = (
        scheduler.create_schedule(
            Name=name,
            ScheduleExpression=(
                expression
            ),
            ScheduleExpressionTimezone=(
                "UTC"
            ),
            FlexibleTimeWindow={
                "Mode": "OFF",
            },
            Target={
                "Arn": lambda_arn,
                "RoleArn": role_arn,
                "Input": payload,
            },
            ActionAfterCompletion=(
                "DELETE"
            ),
        )
    )

    run_at_iso = (
        run_at_utc.isoformat()
    )

    if persist_task:
        task[
            "wait_schedule_name"
        ] = name

        task[
            "wait_scheduled_for"
        ] = run_at_iso

        task[
            "wait_status"
        ] = "SCHEDULED"

        save_task(task)

        record_event(
            task_id,
            "WAIT_SCHEDULED",
            {
                "schedule_name": name,
                "run_at_utc": (
                    run_at_iso
                ),
                "source": (
                    "EventBridge Scheduler"
                ),
            },
        )

    return {
        "schedule_name": name,
        "task_id": task_id,
        "run_at_utc": run_at_iso,
        "schedule_arn": (
            response["ScheduleArn"]
        ),
        "wait_status": "SCHEDULED",
        "message": (
            "Relay persisted the task "
            "and scheduled an automatic "
            "future resume."
            if persist_task
            else
            "Relay scheduled an automatic "
            "future resume."
        ),
    }


def schedule_resume_in_minutes(
    task_id: str,
    minutes: int,
) -> dict:
    if minutes < 1:
        return {
            "error": (
                "minutes must be "
                "at least 1"
            )
        }

    if minutes > 60:
        return {
            "error": (
                "Demo resume delay "
                "cannot exceed 60 minutes."
            )
        }

    run_at = (
        datetime.now(
            timezone.utc,
        )
        + timedelta(
            minutes=minutes,
        )
    )

    return schedule_resume(
        task_id=task_id,
        run_at=run_at,
    )