from __future__ import annotations

import json
import os
import traceback

import boto3

from relay.audit import delete_task_events
from relay.scheduler import delete_resume_schedule
from relay.scam.service import (
    get_protection_case_logic,
    open_protection_case_logic,
)
from relay.store import delete_task


REGION = "us-west-2"
FUNCTION_NAME = "RelayResumeWorker"
OWNER_ID = "user_savita"
TEST_SECRET = "relay-task12-lambda-secret-not-for-production"


def passed(message: str) -> None:
    print(f"PASS: {message}")


def cleanup_case(case_id: str | None) -> None:
    if not case_id:
        return

    for suffix in [
        "e1",
        "e2",
        "e3",
        "e4",
        "e5",
        "exp",
    ]:
        try:
            delete_resume_schedule(
                case_id,
                name_suffix=suffix,
            )
        except Exception:
            pass

    try:
        delete_task_events(case_id)
    except Exception:
        pass

    try:
        delete_task(case_id)
    except Exception:
        pass


def invoke_lambda(
    client,
    payload: dict,
) -> dict:
    response = client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode(
            "utf-8"
        ),
    )

    if response.get("FunctionError"):
        body = response["Payload"].read().decode(
            "utf-8"
        )

        raise RuntimeError(
            "Lambda returned FunctionError: "
            + body
        )

    raw = response["Payload"].read()

    if not raw:
        raise RuntimeError(
            "Lambda returned an empty response"
        )

    result = json.loads(
        raw.decode("utf-8")
    )

    if result.get("statusCode") != 200:
        raise RuntimeError(
            f"Unexpected Lambda response: {result}"
        )

    return result


def open_test_case() -> str:
    opened = open_protection_case_logic(
        owner_id=OWNER_ID,
        risk_score=85,
        amount=25000,
        payee_label="Task 12 Lambda payee",
        payee_is_new=True,
        signals=[
            "impersonation",
            "urgency",
            "payment_demand",
        ],
        cooling_off_minutes=10,
    )

    if opened.get("error"):
        raise RuntimeError(
            f"Could not create test case: {opened['error']}"
        )

    case_id = opened.get("task_id")

    if not case_id:
        raise RuntimeError(
            "Protection case returned no task_id"
        )

    return case_id


def main() -> None:
    os.environ.setdefault(
        "RELAY_SHIELD_SECRET",
        TEST_SECRET,
    )

    lambda_client = boto3.client(
        "lambda",
        region_name=REGION,
    )

    escalation_case: str | None = None
    expiry_case: str | None = None

    try:
        print("=" * 70)
        print("RELAY SHIELD AWS INTEGRATION TEST: REAL LAMBDA")
        print("=" * 70)

        escalation_case = open_test_case()

        before = get_protection_case_logic(
            escalation_case,
            OWNER_ID,
        )

        assert (
            before.get("status")
            == "AWAITING_FAMILY"
        ), before

        assert (
            before.get("current_contact_index")
            == 0
        ), before

        passed(
            "fresh escalation case created"
        )

        first = invoke_lambda(
            lambda_client,
            {
                "task_id": escalation_case,
                "step": "ESCALATE",
                "to_index": 1,
            },
        )

        after = get_protection_case_logic(
            escalation_case,
            OWNER_ID,
        )

        assert (
            after.get("status")
            == "AWAITING_FAMILY"
        ), after

        assert (
            after.get("current_contact_index")
            == 1
        ), after

        approvals = after.get(
            "approvals",
            {},
        )

        assert "c_anita" in approvals, after

        assert (
            first.get("result")
            == "applied"
        ), first

        passed(
            "real Lambda escalated from Rohan to Anita"
        )

        repeated = invoke_lambda(
            lambda_client,
            {
                "task_id": escalation_case,
                "step": "ESCALATE",
                "to_index": 1,
            },
        )

        repeated_case = get_protection_case_logic(
            escalation_case,
            OWNER_ID,
        )

        assert (
            repeated_case.get(
                "current_contact_index"
            )
            == 1
        ), repeated_case

        assert (
            repeated.get("result")
            == "skipped"
        ), repeated

        passed(
            "duplicate ESCALATE delivery was skipped"
        )

        expiry_case = open_test_case()

        expiry_before = get_protection_case_logic(
            expiry_case,
            OWNER_ID,
        )

        assert (
            expiry_before.get("status")
            == "AWAITING_FAMILY"
        ), expiry_before

        expired = invoke_lambda(
            lambda_client,
            {
                "task_id": expiry_case,
                "step": "EXPIRE",
            },
        )

        expiry_after = get_protection_case_logic(
            expiry_case,
            OWNER_ID,
        )

        assert (
            expiry_after.get("status")
            == "EXPIRED_BLOCKED"
        ), expiry_after

        assert (
            expiry_after.get(
                "payment_status"
            )
            == "BLOCKED"
        ), expiry_after

        assert (
            expiry_after.get("approved")
            is False
        ), expiry_after

        assert (
            expired.get("result")
            == "applied"
        ), expired

        passed(
            "real Lambda expiry kept the payment blocked"
        )

        expired_again = invoke_lambda(
            lambda_client,
            {
                "task_id": expiry_case,
                "step": "EXPIRE",
            },
        )

        assert (
            expired_again.get("result")
            == "skipped"
        ), expired_again

        passed(
            "duplicate EXPIRE delivery was skipped"
        )

        print()
        print("=" * 70)
        print("RELAY SHIELD LAMBDA INTEGRATION TEST PASSED")
        print("=" * 70)

    except Exception:
        print()
        print("FAIL: Relay Shield Lambda integration test")
        traceback.print_exc()
        raise

    finally:
        cleanup_case(escalation_case)
        cleanup_case(expiry_case)


if __name__ == "__main__":
    main()