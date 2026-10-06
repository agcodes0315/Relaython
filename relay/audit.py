import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Key


AWS_REGION = os.environ.get(
    "AWS_REGION",
    "us-west-2",
)

AUDIT_TABLE_NAME = os.environ.get(
    "RELAY_AUDIT_TABLE",
    "RelayAudit",
)


dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION,
)

audit_table = dynamodb.Table(
    AUDIT_TABLE_NAME
)


def _to_decimal(
    value: Any,
) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {
            key: _to_decimal(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _to_decimal(item)
            for item in value
        ]

    return value


def _from_decimal(
    value: Any,
) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)

        return float(value)

    if isinstance(value, dict):
        return {
            key: _from_decimal(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _from_decimal(item)
            for item in value
        ]

    return value


def record_event(
    task_id: str,
    event_type: str,
    details: dict,
) -> dict:
    """
    Persist an immutable audit event for one Relay task.
    """

    event = {
        "task_id": task_id,
        "event_id": (
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y%m%dT%H%M%S%fZ"
            )
            + "-"
            + str(uuid4())
        ),
        "event_type": event_type,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "details": details,
    }

    audit_table.put_item(
        Item=_to_decimal(event)
    )

    return event


def get_task_events(
    task_id: str,
) -> list[dict]:
    """
    Return all audit events for a task in
    chronological order.
    """

    response = audit_table.query(
        KeyConditionExpression=(
            Key("task_id").eq(
                task_id
            )
        ),
        ScanIndexForward=True,
    )

    items = response.get(
        "Items",
        [],
    )

    return [
        _from_decimal(item)
        for item in items
    ]


def delete_task_events(
    task_id: str,
) -> None:
    """
    Delete test audit data for one task.
    """

    events = get_task_events(
        task_id
    )

    if not events:
        return

    with audit_table.batch_writer() as batch:
        for event in events:
            batch.delete_item(
                Key={
                    "task_id": (
                        event["task_id"]
                    ),
                    "event_id": (
                        event["event_id"]
                    ),
                }
            )
