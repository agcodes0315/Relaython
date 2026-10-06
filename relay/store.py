import os
from decimal import Decimal
from typing import Any

import boto3


AWS_REGION = os.environ.get(
    "AWS_REGION",
    "us-west-2",
)

TASKS_TABLE_NAME = os.environ.get(
    "RELAY_TASKS_TABLE",
    "RelayTasks",
)


dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION,
)

tasks_table = dynamodb.Table(
    TASKS_TABLE_NAME
)


def _to_decimal(
    value: Any,
) -> Any:
    """
    Convert floats to Decimal because DynamoDB
    does not support Python float values directly.
    """

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
    """
    Convert DynamoDB Decimal values back into
    normal Python int/float values.
    """

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


def save_task(
    task: dict,
) -> dict:
    """
    Persist the full current Relay task state
    into DynamoDB.
    """

    tasks_table.put_item(
        Item=_to_decimal(task)
    )

    return task


def get_task(
    task_id: str,
) -> dict | None:
    """
    Retrieve one Relay task from DynamoDB.
    """

    response = tasks_table.get_item(
        Key={
            "task_id": task_id
        }
    )

    item = response.get("Item")

    if item is None:
        return None

    return _from_decimal(item)


def delete_task(
    task_id: str,
) -> None:
    """
    Delete a task. Mainly useful for tests.
    """

    tasks_table.delete_item(
        Key={
            "task_id": task_id
        }
    )
