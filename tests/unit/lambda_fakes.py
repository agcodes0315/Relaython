from __future__ import annotations

import copy
import importlib.util
from decimal import Decimal
from pathlib import Path

from botocore.exceptions import ClientError

HANDLER_PATH = (
    Path(__file__).resolve().parents[2]
    / "lambda"
    / "resume_worker"
    / "handler.py"
)

HOLD_START = "2026-10-14T10:00:00+00:00"
HOLD_END = "2026-10-14T10:30:00+00:00"


def to_dynamo(value):
    """Mimic DynamoDB: ints and floats come back as Decimal."""
    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return Decimal(value)

    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {k: to_dynamo(v) for k, v in value.items()}

    if isinstance(value, list):
        return [to_dynamo(v) for v in value]

    return value


def client_error(code: str, operation: str = "UpdateItem") -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": code}},
        operation,
    )


class FakeTasksTable:
    def __init__(self, items=None):
        self.items: dict[str, dict] = {}
        self.update_calls: list[dict] = []

        for item in items or []:
            self.put(item)

    def put(self, item: dict) -> None:
        self.items[item["task_id"]] = to_dynamo(copy.deepcopy(item))

    def get(self, task_id: str) -> dict:
        return copy.deepcopy(self.items[task_id])

    def get_item(self, Key):
        item = self.items.get(Key["task_id"])

        if item is None:
            return {}

        return {"Item": copy.deepcopy(item)}

    # -- conditions: only 'attr = :value' joined by AND ----------------
    def _check_condition(self, item, condition, names, values):
        if not condition:
            return

        for clause in condition.split(" AND "):
            clause = clause.strip().strip("()")
            left, separator, right = clause.partition(" = ")

            if not separator or "." in left:
                raise NotImplementedError(f"fake cannot read: {clause}")

            attribute = names.get(left, left)

            if item.get(attribute) != values[right]:
                raise client_error("ConditionalCheckFailedException")

    # -- updates: SET a = :x, b.#c = :y   [ADD n :v] -------------------
    def _apply_update(self, item, expression, names, values):
        set_part, add_part = expression.strip(), ""

        if " ADD " in set_part:
            set_part, add_part = set_part.split(" ADD ", 1)

        if set_part.startswith("SET "):
            for assignment in set_part[4:].split(","):
                path, _, placeholder = assignment.partition(" = ")
                parts = [
                    names.get(p.strip(), p.strip())
                    for p in path.strip().split(".")
                ]

                parent = item

                for part in parts[:-1]:
                    parent = parent.get(part)

                    if not isinstance(parent, dict):
                        raise client_error("ValidationException")

                parent[parts[-1]] = copy.deepcopy(values[placeholder.strip()])

        if add_part.strip():
            attribute, placeholder = add_part.strip().split()
            attribute = names.get(attribute, attribute)
            item[attribute] = item.get(attribute, 0) + values[placeholder]

    def update_item(
        self,
        Key,
        UpdateExpression,
        ExpressionAttributeValues=None,
        ExpressionAttributeNames=None,
        ConditionExpression=None,
        ReturnValues=None,
        **_ignored,
    ):
        names = ExpressionAttributeNames or {}
        values = to_dynamo(ExpressionAttributeValues or {})
        task_id = Key["task_id"]
        item = self.items[task_id]

        record = {
            "task_id": task_id,
            "update": UpdateExpression,
            "condition": ConditionExpression,
            "applied": False,
        }
        self.update_calls.append(record)

        self._check_condition(item, ConditionExpression, names, values)

        updated = copy.deepcopy(item)
        self._apply_update(updated, UpdateExpression, names, values)
        self.items[task_id] = updated
        record["applied"] = True

        if ReturnValues == "ALL_NEW":
            return {"Attributes": copy.deepcopy(updated)}

        return {}

    @property
    def applied_updates(self) -> list[dict]:
        return [c for c in self.update_calls if c["applied"]]


class FakeAuditTable:
    def __init__(self):
        self.items: list[dict] = []

    def put_item(self, Item):
        self.items.append(copy.deepcopy(Item))

    def types(self) -> list[str]:
        return [item["event_type"] for item in self.items]

    def of_type(self, event_type: str) -> list[dict]:
        return [i for i in self.items if i["event_type"] == event_type]


def load_handler(monkeypatch, items=None):
    """Import the real handler.py and attach fake tables to it."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")

    spec = importlib.util.spec_from_file_location(
        "relay_resume_handler_under_test",
        HANDLER_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.tasks_table = FakeTasksTable(items)
    module.audit_table = FakeAuditTable()

    return module


def make_case(**overrides) -> dict:
    """A held payment waiting for the first family contact (Rohan)."""
    case = {
        "task_id": "case-test-1",
        "kind": "scam_case",
        "owner_id": "user_savita",
        "status": "AWAITING_FAMILY",
        "risk_score": 85,
        "risk_level": "CRITICAL",
        "signals": ["otp_request", "impersonation"],
        "amount": 25000,
        "payee_label": "Payee 98******10",
        "payee_is_new": True,
        "decision": "HOLD",
        "reasons": ["Scam risk is high and a payment is being made."],
        "contacts": [
            {"contact_id": "c_rohan", "name": "Rohan", "order": 1},
            {"contact_id": "c_anita", "name": "Anita", "order": 2},
        ],
        "current_contact_index": 0,
        "approvals": {
            "c_rohan": {
                "issued_at": HOLD_START,
                "expires_at": HOLD_END,
                "used": False,
                "attempts": 0,
            }
        },
        "cooling_off_minutes": 30,
        "payment_status": "HELD",
        "approved": False,
        "created_at": HOLD_START,
        "hold_started_at": HOLD_START,
        "hold_expires_at": HOLD_END,
    }
    case.update(overrides)

    return case


def make_plain_task(**overrides) -> dict:
    """An ordinary errand task (not a scam case)."""
    task = {
        "task_id": "task-plain-1",
        "goal": "Get my AC serviced",
        "budget": 2000,
        "deadline": "this week",
        "excluded_days": ["Thursday"],
        "status": "SEARCHING",
        "approved": False,
    }
    task.update(overrides)

    return task


ESCALATE_TO_1 = {"task_id": "case-test-1", "step": "ESCALATE", "to_index": 1}
EXPIRE = {"task_id": "case-test-1", "step": "EXPIRE"}