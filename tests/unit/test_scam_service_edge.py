from __future__ import annotations

import json
from decimal import Decimal

import pytest
from botocore.exceptions import ClientError

import relay.scam.service as service


class FakeTasksTable:
    def __init__(
        self,
        *,
        fail_code=None,
    ):
        self.calls = []
        self.fail_code = fail_code

    def update_item(
        self,
        **kwargs,
    ):
        self.calls.append(kwargs)

        if self.fail_code:
            raise ClientError(
                {
                    "Error": {
                        "Code": self.fail_code,
                        "Message": "test",
                    }
                },
                "UpdateItem",
            )

        return {
            "Attributes": {
                "task_id": kwargs["Key"]["task_id"],
                "status": "HELD",
                "amount": Decimal("125.5"),
            }
        }


def test_conditional_update_uses_status_placeholder(
    monkeypatch,
):
    fake = FakeTasksTable()

    monkeypatch.setattr(
        service,
        "tasks_table",
        fake,
    )

    result = service._conditional_update(
        "case-1",
        "OPENED",
        {
            "status": "HELD",
            "amount": 125.5,
        },
    )

    call = fake.calls[0]

    assert "#s = :expected_status" in (
        call["ConditionExpression"]
    )

    assert (
        call["ExpressionAttributeNames"]["#s"]
        == "status"
    )

    update_text = call[
        "UpdateExpression"
    ]

    assert " status " not in (
        f" {update_text} "
    )

    assert result is not None


def test_float_becomes_decimal(
    monkeypatch,
):
    fake = FakeTasksTable()

    monkeypatch.setattr(
        service,
        "tasks_table",
        fake,
    )

    service._conditional_update(
        "case-1",
        "OPENED",
        {
            "amount": 125.5,
        },
    )

    values = (
        fake.calls[0][
            "ExpressionAttributeValues"
        ]
    )

    assert any(
        isinstance(value, Decimal)
        for value in values.values()
    )


def test_conditional_failure_returns_none(
    monkeypatch,
):
    monkeypatch.setattr(
        service,
        "tasks_table",
        FakeTasksTable(
            fail_code=(
                "ConditionalCheckFailedException"
            )
        ),
    )

    result = service._conditional_update(
        "case-1",
        "OPENED",
        {
            "status": "HELD",
        },
    )

    assert result is None


def test_other_dynamodb_errors_propagate(
    monkeypatch,
):
    monkeypatch.setattr(
        service,
        "tasks_table",
        FakeTasksTable(
            fail_code=(
                "ProvisionedThroughputExceededException"
            )
        ),
    )

    with pytest.raises(
        ClientError
    ):
        service._conditional_update(
            "case-1",
            "OPENED",
            {
                "status": "HELD",
            },
        )


def test_returned_case_is_json_serializable(
    monkeypatch,
):
    monkeypatch.setattr(
        service,
        "save_task",
        lambda task: task,
    )

    monkeypatch.setattr(
        service,
        "record_event",
        lambda *args: None,
    )

    case = (
        service
        .open_protection_case_logic(
            "user_savita",
            85,
            25000,
            "Payee 9876543210",
            True,
            [
                "otp_request",
            ],
        )
    )

    json.dumps(case)


def test_none_amount_high_risk_does_not_raise(
    monkeypatch,
):
    monkeypatch.setattr(
        service,
        "save_task",
        lambda task: task,
    )

    monkeypatch.setattr(
        service,
        "record_event",
        lambda *args: None,
    )

    case = (
        service
        .open_protection_case_logic(
            "user_savita",
            90,
            None,
            "Payee",
            True,
        )
    )

    assert case["status"] == (
        "WARNED"
    )


def test_none_cooling_period_uses_profile_default(
    monkeypatch,
):
    monkeypatch.setattr(
        service,
        "save_task",
        lambda task: task,
    )

    monkeypatch.setattr(
        service,
        "record_event",
        lambda *args: None,
    )

    case = (
        service
        .open_protection_case_logic(
            "user_savita",
            85,
            25000,
            "Payee",
            True,
            cooling_off_minutes=None,
        )
    )

    assert (
        case["cooling_off_minutes"]
        == 30
    )


def test_raw_payee_number_never_reaches_storage_or_audit(
    monkeypatch,
):
    saved = []
    events = []

    monkeypatch.setattr(
        service,
        "save_task",
        lambda task: saved.append(
            dict(task)
        ),
    )

    monkeypatch.setattr(
        service,
        "record_event",
        lambda *args: events.append(
            args
        ),
    )

    service.open_protection_case_logic(
        "user_savita",
        85,
        25000,
        "Payee 9876543210",
        True,
        ["otp_request"],
    )

    combined = json.dumps(
        {
            "saved": saved,
            "events": events,
        }
    )

    assert "9876543210" not in combined


def test_profile_mutation_does_not_change_demo_profiles():
    from relay.scam import data

    original = data.get_profile(
        "user_savita"
    )

    original_name = (
        original["contacts"][0][
            "name"
        ]
    )

    copied_profile = data.get_profile(
        "user_savita"
    )

    copied_profile[
        "contacts"
    ][0]["name"] = "MUTATED"

    fresh = data.get_profile(
        "user_savita"
    )

    assert (
        fresh["contacts"][0]["name"]
        == original_name
    )