import json
import os
from datetime import datetime, timedelta, timezone

import boto3


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
    region_name=AWS_REGION,
)

lambda_client = boto3.client(
    "lambda",
    region_name=AWS_REGION,
)


def _schedule_name(
    task_id: str,
) -> str:
    safe_id = (
        task_id
        .replace("_", "-")
        .replace(":", "-")
    )

    return f"relay-resume-{safe_id}"[:64]


def schedule_resume(
    task_id: str,
    run_at: datetime,
) -> dict:
    if run_at.tzinfo is None:
        run_at = run_at.replace(
            tzinfo=timezone.utc
        )

    run_at_utc = run_at.astimezone(
        timezone.utc
    )

    role_arn = iam.get_role(
        RoleName=SCHEDULER_ROLE_NAME
    )["Role"]["Arn"]

    lambda_arn = lambda_client.get_function(
        FunctionName=LAMBDA_FUNCTION_NAME
    )["Configuration"]["FunctionArn"]

    expression = (
        "at("
        + run_at_utc.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        + ")"
    )

    name = _schedule_name(
        task_id
    )

    payload = json.dumps(
        {
            "task_id": task_id
        }
    )

    try:
        scheduler.delete_schedule(
            Name=name
        )
    except scheduler.exceptions.ResourceNotFoundException:
        pass

    response = scheduler.create_schedule(
        Name=name,
        ScheduleExpression=expression,
        ScheduleExpressionTimezone="UTC",
        FlexibleTimeWindow={
            "Mode": "OFF"
        },
        Target={
            "Arn": lambda_arn,
            "RoleArn": role_arn,
            "Input": payload,
        },
        ActionAfterCompletion="DELETE",
    )

    return {
        "schedule_name": name,
        "task_id": task_id,
        "run_at_utc": (
            run_at_utc.isoformat()
        ),
        "schedule_arn": (
            response["ScheduleArn"]
        ),
    }


def schedule_resume_in_minutes(
    task_id: str,
    minutes: int,
) -> dict:
    run_at = (
        datetime.now(
            timezone.utc
        )
        + timedelta(
            minutes=minutes
        )
    )

    return schedule_resume(
        task_id=task_id,
        run_at=run_at,
    )
