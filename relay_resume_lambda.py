import os
from datetime import datetime, timezone
from uuid import uuid4

import boto3


REGION = os.environ.get("AWS_REGION", "us-west-2")
TASKS_TABLE = os.environ.get(
    "RELAY_TASKS_TABLE",
    "RelayTasks",
)
AUDIT_TABLE = os.environ.get(
    "RELAY_AUDIT_TABLE",
    "RelayAudit",
)


dynamodb = boto3.resource(
    "dynamodb",
    region_name=REGION,
)

tasks_table = dynamodb.Table(
    TASKS_TABLE
)

audit_table = dynamodb.Table(
    AUDIT_TABLE
)


def lambda_handler(event, context):
    print("Relay resume worker invoked.")
    print(event)

    task_id = event.get("task_id")

    if not task_id:
        return {
            "statusCode": 400,
            "message": "task_id is required",
        }

    response = tasks_table.get_item(
        Key={
            "task_id": task_id
        }
    )

    task = response.get("Item")

    if task is None:
        return {
            "statusCode": 404,
            "task_id": task_id,
            "message": "Relay task not found",
        }

    now = datetime.now(
        timezone.utc
    )

    event_id = (
        now.strftime(
            "%Y%m%dT%H%M%S%fZ"
        )
        + "-"
        + str(uuid4())
    )

    audit_event = {
        "task_id": task_id,
        "event_id": event_id,
        "event_type": "RESUME_TRIGGERED",
        "timestamp": now.isoformat(),
        "details": {
            "source": "EventBridge Scheduler",
            "current_status": task.get(
                "status",
                "UNKNOWN",
            ),
            "message": (
                "Relay was automatically "
                "woken to inspect this task."
            ),
        },
    }

    audit_table.put_item(
        Item=audit_event
    )

    print(
        "Resume event written for:",
        task_id,
    )

    return {
        "statusCode": 200,
        "task_id": task_id,
        "task_status": task.get(
            "status"
        ),
        "message": (
            "Relay resume worker completed."
        ),
    }
