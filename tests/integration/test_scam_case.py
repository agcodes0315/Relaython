from __future__ import annotations

import os
import traceback

from relay.audit import delete_task_events, get_task_events
from relay.scheduler import delete_resume_schedule
from relay.scam.service import (
    alert_trusted_contact_logic,
    get_family_inbox_logic,
    get_protection_case_logic,
    open_protection_case_logic,
    record_family_decision_logic,
)
from relay.store import delete_task


OWNER_ID = "user_savita"
TEST_SECRET = "relay-task12-integration-secret-not-for-production"


def passed(message: str) -> None:
    print(f"PASS: {message}")


def cleanup_case(case_id: str | None) -> None:
    if not case_id:
        return

    print("Cleaning up integration case...")

    # Relay Shield currently creates escalation suffixes e1... and exp.
    # Delete several possible escalation schedules defensively.
    for suffix in ["e1", "e2", "e3", "e4", "e5", "exp"]:
        try:
            delete_resume_schedule(
                case_id,
                name_suffix=suffix,
            )
        except Exception:
            # Cleanup must continue even if a schedule never existed
            # or has already fired/deleted itself.
            pass

    try:
        delete_task_events(case_id)
    except Exception:
        pass

    try:
        delete_task(case_id)
    except Exception:
        pass


def main() -> None:
    os.environ.setdefault(
        "RELAY_SHIELD_SECRET",
        TEST_SECRET,
    )

    case_id: str | None = None

    try:
        print("=" * 70)
        print("RELAY SHIELD AWS INTEGRATION TEST: CASE FLOW")
        print("=" * 70)

        opened = open_protection_case_logic(
            owner_id=OWNER_ID,
            risk_score=85,
            amount=25000,
            payee_label="New electricity payee",
            payee_is_new=True,
            signals=[
                "impersonation",
                "urgency",
                "payment_demand",
            ],
            cooling_off_minutes=10,
        )

        if opened.get("error"):
            raise AssertionError(
                f"Opening protection case failed: {opened['error']}"
            )

        case_id = opened.get("task_id")

        if not case_id:
            raise AssertionError(
                "open_protection_case_logic returned no task_id"
            )

        stored = get_protection_case_logic(
            case_id,
            OWNER_ID,
        )

        assert (
            stored.get("status")
            == "AWAITING_FAMILY"
        ), stored

        assert (
            stored.get("payment_status")
            == "HELD"
        ), stored

        assert (
            stored.get("current_contact_index")
            == 0
        ), stored

        approvals = stored.get(
            "approvals",
            {},
        )

        assert "c_rohan" in approvals, stored

        passed(
            "HOLD case moved to AWAITING_FAMILY and alerted Rohan"
        )

        repeated = alert_trusted_contact_logic(
            case_id,
            OWNER_ID,
        )

        assert (
            repeated.get("already_alerted")
            is True
        ), repeated

        passed(
            "repeated alert is idempotent"
        )

        wrong = record_family_decision_logic(
            case_id=case_id,
            contact_id="c_rohan",
            approval_code="00000000",
            decision="APPROVE",
        )

        assert wrong.get("error"), wrong

        after_wrong = get_protection_case_logic(
            case_id,
            OWNER_ID,
        )

        assert (
            after_wrong.get("status")
            == "AWAITING_FAMILY"
        ), after_wrong

        passed(
            "wrong approval code was rejected"
        )

        inbox = get_family_inbox_logic(
            case_id,
            "c_rohan",
        )

        assert (
            inbox.get("found")
            is True
        ), inbox

        code = inbox.get("approval_code")

        assert code, (
            "Family inbox did not return an approval code"
        )

        # Never print the approval code itself.
        passed(
            "family approval code received privately"
        )

        approved = record_family_decision_logic(
            case_id=case_id,
            contact_id="c_rohan",
            approval_code=code,
            decision="APPROVE",
        )

        assert (
            approved.get("status")
            == "APPROVED"
        ), approved

        final_case = get_protection_case_logic(
            case_id,
            OWNER_ID,
        )

        assert (
            final_case.get("status")
            == "APPROVED"
        ), final_case

        assert (
            final_case.get("payment_status")
            == "RELEASED"
        ), final_case

        passed(
            "valid family approval released the held payment"
        )

        second = record_family_decision_logic(
            case_id=case_id,
            contact_id="c_rohan",
            approval_code=code,
            decision="APPROVE",
        )

        assert (
            second.get("error")
            == "Case already decided"
        ), second

        passed(
            "second family decision was refused"
        )

        events = get_task_events(case_id)

        event_types = {
            event.get("event_type")
            for event in events
        }

        assert (
            "CONTACT_ALERTED"
            in event_types
        ), event_types

        assert (
            "FAMILY_APPROVED"
            in event_types
        ), event_types

        passed(
            "audit trail contains CONTACT_ALERTED and FAMILY_APPROVED"
        )

        print()
        print("=" * 70)
        print("RELAY SHIELD CASE INTEGRATION TEST PASSED")
        print("=" * 70)

    except Exception:
        print()
        print("FAIL: Relay Shield case integration test")
        traceback.print_exc()
        raise

    finally:
        cleanup_case(case_id)


if __name__ == "__main__":
    main()