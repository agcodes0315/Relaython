import ast
import copy

import pytest

from lambda_fakes import (
    HANDLER_PATH,
    HOLD_END,
    load_handler,
    make_case,
    make_plain_task,
)

SOURCE = HANDLER_PATH.read_text(encoding="utf-8")

ALL_STATUSES = [
    "OPENED",
    "WARNED",
    "HELD",
    "AWAITING_FAMILY",
    "CLEARED",
    "BLOCKED",
    "APPROVED",
    "REJECTED",
    "EXPIRED_BLOCKED",
]

# Names that stand for a whole event or task record in the handler.
WHOLE_OBJECT_NAMES = {"event", "task", "response", "updated", "resumed_task", "item"}


def escalate(to_index, task_id="case-test-1"):
    return {"task_id": task_id, "step": "ESCALATE", "to_index": to_index}


def expire(task_id="case-test-1"):
    return {"task_id": task_id, "step": "EXPIRE"}


# ------------------------------------------------------------------ static


def test_handler_does_not_import_the_relay_package():
    tree = ast.parse(SOURCE)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] != "relay", alias.name

        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] != "relay", node.module


def test_handler_uses_only_the_standard_library_and_boto():
    allowed = {
        "os", "datetime", "uuid", "boto3", "botocore", "__future__",
        "json", "decimal", "typing",
    }
    tree = ast.parse(SOURCE)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in allowed, alias.name

        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in allowed, node.module


def _exposes_whole_object(node) -> bool:
    """True when a print argument would show a whole event or task.

    A single field such as event.get('step') or task['status'] is fine.
    """
    if isinstance(node, ast.Name):
        return node.id in WHOLE_OBJECT_NAMES

    if isinstance(node, (ast.Attribute, ast.Subscript)):
        return False

    return any(_exposes_whole_object(child) for child in ast.iter_child_nodes(node))


def test_no_print_call_receives_the_whole_event_or_task():
    tree = ast.parse(SOURCE)
    prints = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]

    assert prints, "expected the handler to log something"

    for call in prints:
        for argument in call.args:
            assert not _exposes_whole_object(argument), ast.dump(call)


def test_the_handler_never_mentions_a_released_payment():
    assert "RELEASED" not in SOURCE


def test_scam_handling_comes_before_the_old_resume_logic():
    tree = ast.parse(SOURCE)
    handler = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "lambda_handler"
    )
    text = ast.get_source_segment(SOURCE, handler)

    assert text.index("_handle_scam_case") < text.index("RESUME_TRIGGERED")


# ---------------------------------------------------------- compatibility


def test_plain_task_keeps_the_old_behaviour_and_counts_resumes(monkeypatch):
    handler = load_handler(monkeypatch, [make_plain_task()])

    first = handler.lambda_handler({"task_id": "task-plain-1"}, None)
    second = handler.lambda_handler({"task_id": "task-plain-1"}, None)
    stored = handler.tasks_table.get("task-plain-1")

    assert first["resume_count"] == 1
    assert second["resume_count"] == 2
    assert stored["wait_status"] == "RESUMED"
    assert stored["last_resume_source"] == "EventBridge Scheduler"
    assert stored["status"] == "SEARCHING"      # business status untouched
    assert stored["approved"] is False
    assert handler.audit_table.types() == [
        "RESUME_TRIGGERED", "STATE_RESTORED", "TASK_RESUMED",
    ] * 2


def test_plain_task_with_a_step_field_is_still_a_plain_resume(monkeypatch):
    # Only scam cases look at 'step'. An errand must never be escalated.
    handler = load_handler(monkeypatch, [make_plain_task(status="AWAITING_FAMILY")])

    response = handler.lambda_handler(
        {"task_id": "task-plain-1", "step": "EXPIRE"}, None
    )

    assert response["message"] == "Relay restored and resumed the durable task."
    assert handler.tasks_table.get("task-plain-1")["status"] == "AWAITING_FAMILY"


def test_missing_task_and_missing_task_id_keep_their_old_shapes(monkeypatch):
    handler = load_handler(monkeypatch)

    assert handler.lambda_handler({"task_id": "x"}, None) == {
        "statusCode": 404, "task_id": "x", "message": "Relay task not found",
    }
    assert handler.lambda_handler({}, None) == {
        "statusCode": 400, "message": "task_id is required",
    }
    assert handler.lambda_handler({"task_id": ""}, None)["statusCode"] == 400


def test_a_non_dict_event_returns_400_instead_of_crashing(monkeypatch):
    handler = load_handler(monkeypatch)

    for event in [None, "text", 42, ["case-test-1"]]:
        assert handler.lambda_handler(event, None)["statusCode"] == 400


# --------------------------------------------------------------- ESCALATE


def test_escalation_follows_the_order_field_not_the_list_position(monkeypatch):
    # Contacts are stored in REVERSE order: Anita (order 2) is listed first.
    case = make_case(
        contacts=[
            {"contact_id": "c_anita", "name": "Anita", "order": 2},
            {"contact_id": "c_rohan", "name": "Rohan", "order": 1},
        ]
    )
    handler = load_handler(monkeypatch, [case])

    response = handler.lambda_handler(escalate(1), None)
    stored = handler.tasks_table.get("case-test-1")
    event = handler.audit_table.of_type("ESCALATED")[0]["details"]

    assert response["result"] == "applied"
    assert "c_anita" in stored["approvals"]          # second by ORDER
    assert event["from_contact_id"] == "c_rohan"
    assert event["to_contact_id"] == "c_anita"


def test_the_new_approval_entry_is_complete(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])

    handler.lambda_handler(escalate(1), None)
    entry = handler.tasks_table.get("case-test-1")["approvals"]["c_anita"]

    assert set(entry.keys()) == {"issued_at", "expires_at", "used", "attempts"}
    assert entry["issued_at"]
    assert entry["expires_at"] == HOLD_END
    assert entry["used"] is False
    assert entry["attempts"] == 0


def test_escalation_keeps_the_first_contacts_entry_untouched(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])
    before = handler.tasks_table.get("case-test-1")["approvals"]["c_rohan"]

    handler.lambda_handler(escalate(1), None)

    after = handler.tasks_table.get("case-test-1")["approvals"]["c_rohan"]
    assert after == before


def test_a_duplicate_escalate_changes_nothing_and_is_logged(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])

    handler.lambda_handler(escalate(1), None)
    snapshot = handler.tasks_table.get("case-test-1")
    issued_at = snapshot["approvals"]["c_anita"]["issued_at"]

    for _ in range(3):
        again = handler.lambda_handler(escalate(1), None)

        assert again["result"] == "skipped"

    assert handler.tasks_table.get("case-test-1") == snapshot
    assert handler.tasks_table.get("case-test-1")["approvals"]["c_anita"]["issued_at"] == issued_at
    assert len(handler.audit_table.of_type("ESCALATED")) == 1
    assert len(handler.audit_table.of_type("ESCALATE_SKIPPED")) == 3


def test_escalate_to_a_contact_that_does_not_exist_changes_nothing(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])
    before = handler.tasks_table.get("case-test-1")

    response = handler.lambda_handler(escalate(5), None)

    assert response["statusCode"] == 200
    assert response["result"] == "skipped"
    assert handler.tasks_table.get("case-test-1") == before
    assert handler.tasks_table.applied_updates == []


def test_escalate_with_a_bad_to_index_is_skipped_without_raising(monkeypatch):
    for bad in [0, -1, 2, "1", None, True, 1.0, [1], {"a": 1}]:
        handler = load_handler(monkeypatch, [make_case()])
        before = handler.tasks_table.get("case-test-1")

        response = handler.lambda_handler(escalate(bad), None)

        assert response["statusCode"] == 200, repr(bad)
        assert response["result"] == "skipped", repr(bad)
        assert handler.tasks_table.get("case-test-1") == before, repr(bad)


def test_escalate_only_works_from_awaiting_family(monkeypatch):
    for status in ALL_STATUSES:
        if status == "AWAITING_FAMILY":
            continue

        handler = load_handler(monkeypatch, [make_case(status=status)])
        before = handler.tasks_table.get("case-test-1")

        response = handler.lambda_handler(escalate(1), None)

        assert response["result"] == "skipped", status
        assert handler.tasks_table.get("case-test-1") == before, status


def test_escalate_needs_the_matching_current_index(monkeypatch):
    # Already on contact 1: an ESCALATE to index 1 is stale and must be skipped.
    case = make_case(current_contact_index=1)
    handler = load_handler(monkeypatch, [case])
    before = handler.tasks_table.get("case-test-1")

    assert handler.lambda_handler(escalate(1), None)["result"] == "skipped"
    assert handler.tasks_table.get("case-test-1") == before

    # Case never alerted (index -1): escalation must not skip ahead either.
    fresh = make_case(current_contact_index=-1)
    handler = load_handler(monkeypatch, [fresh])

    assert handler.lambda_handler(escalate(1), None)["result"] == "skipped"


def test_a_three_contact_chain_escalates_in_order(monkeypatch):
    case = make_case(
        contacts=[
            {"contact_id": "c1", "name": "One", "order": 1},
            {"contact_id": "c2", "name": "Two", "order": 2},
            {"contact_id": "c3", "name": "Three", "order": 3},
        ],
        current_contact_index=0,
        approvals={"c1": {"issued_at": "t", "expires_at": HOLD_END, "used": False, "attempts": 0}},
    )
    handler = load_handler(monkeypatch, [case])

    assert handler.lambda_handler(escalate(2), None)["result"] == "skipped"  # too early
    assert handler.lambda_handler(escalate(1), None)["result"] == "applied"
    assert handler.lambda_handler(escalate(2), None)["result"] == "applied"

    stored = handler.tasks_table.get("case-test-1")

    assert stored["current_contact_index"] == 2
    assert set(stored["approvals"].keys()) == {"c1", "c2", "c3"}


# ----------------------------------------------------------------- EXPIRE


def test_expire_blocks_and_records_everything_once(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])

    response = handler.lambda_handler(expire(), None)
    stored = handler.tasks_table.get("case-test-1")

    assert response["result"] == "applied"
    assert stored["status"] == "EXPIRED_BLOCKED"
    assert stored["payment_status"] == "BLOCKED"
    assert stored["approved"] is False
    assert stored["decided_at"]
    assert len(handler.audit_table.of_type("HOLD_EXPIRED")) == 1
    assert len(handler.audit_table.of_type("PAYMENT_BLOCKED")) == 1


def test_expire_twice_skips_the_second_time_without_duplicate_events(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])

    handler.lambda_handler(expire(), None)
    snapshot = handler.tasks_table.get("case-test-1")

    for _ in range(2):
        assert handler.lambda_handler(expire(), None)["result"] == "skipped"

    assert handler.tasks_table.get("case-test-1") == snapshot
    assert len(handler.audit_table.of_type("HOLD_EXPIRED")) == 1
    assert len(handler.audit_table.of_type("PAYMENT_BLOCKED")) == 1
    assert len(handler.audit_table.of_type("EXPIRE_SKIPPED")) == 2


def test_expire_never_touches_an_approved_case(monkeypatch):
    case = make_case(
        status="APPROVED",
        payment_status="RELEASED",
        approved=True,
        decided_by="c_rohan",
    )
    handler = load_handler(monkeypatch, [case])
    before = handler.tasks_table.get("case-test-1")

    response = handler.lambda_handler(expire(), None)

    assert response["result"] == "skipped"
    assert handler.tasks_table.get("case-test-1") == before
    assert handler.tasks_table.get("case-test-1")["payment_status"] == "RELEASED"
    assert handler.audit_table.types() == ["EXPIRE_SKIPPED"]


def test_expire_never_touches_a_rejected_case(monkeypatch):
    case = make_case(status="REJECTED", payment_status="BLOCKED", approved=False)
    handler = load_handler(monkeypatch, [case])
    before = handler.tasks_table.get("case-test-1")

    assert handler.lambda_handler(expire(), None)["result"] == "skipped"
    assert handler.tasks_table.get("case-test-1") == before


def test_expire_only_acts_on_awaiting_family(monkeypatch):
    for status in ALL_STATUSES:
        if status == "AWAITING_FAMILY":
            continue

        handler = load_handler(monkeypatch, [make_case(status=status)])
        before = handler.tasks_table.get("case-test-1")

        response = handler.lambda_handler(expire(), None)

        assert response["result"] == "skipped", status
        assert handler.tasks_table.get("case-test-1") == before, status


def test_expire_after_an_escalation_still_blocks(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])

    handler.lambda_handler(escalate(1), None)
    handler.lambda_handler(expire(), None)
    stored = handler.tasks_table.get("case-test-1")

    assert stored["status"] == "EXPIRED_BLOCKED"
    assert stored["payment_status"] == "BLOCKED"
    assert "c_anita" in stored["approvals"]


def test_late_escalate_after_expiry_is_skipped(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])

    handler.lambda_handler(expire(), None)
    snapshot = handler.tasks_table.get("case-test-1")

    assert handler.lambda_handler(escalate(1), None)["result"] == "skipped"
    assert handler.tasks_table.get("case-test-1") == snapshot


# -------------------------------------------------------------- robustness


def test_a_case_without_hold_expires_at_does_not_raise(monkeypatch):
    case = make_case()
    del case["hold_expires_at"]

    handler = load_handler(monkeypatch, [case])
    before = handler.tasks_table.get("case-test-1")

    response = handler.lambda_handler(escalate(1), None)

    assert response["statusCode"] == 200
    assert response["result"] in ("ignored", "skipped")
    assert handler.tasks_table.get("case-test-1") == before   # default-deny

    # EXPIRE only ever blocks, so it still works without a deadline.
    expired = handler.lambda_handler(expire(), None)

    assert expired["statusCode"] == 200
    assert handler.tasks_table.get("case-test-1")["payment_status"] == "BLOCKED"


def test_a_case_without_an_approvals_map_is_not_escalated(monkeypatch):
    for approvals in [None, "text", []]:
        case = make_case(approvals=approvals)
        handler = load_handler(monkeypatch, [case])
        before = handler.tasks_table.get("case-test-1")

        response = handler.lambda_handler(escalate(1), None)

        assert response["statusCode"] == 200
        assert response["result"] == "skipped"
        assert handler.tasks_table.get("case-test-1") == before


def test_broken_contact_lists_do_not_raise(monkeypatch):
    for contacts in [None, [], "nope", [None, 5, "x"], [{"name": "no id"}]]:
        handler = load_handler(monkeypatch, [make_case(contacts=contacts)])
        before = handler.tasks_table.get("case-test-1")

        response = handler.lambda_handler(escalate(1), None)

        assert response["statusCode"] == 200
        assert response["result"] == "skipped"
        assert handler.tasks_table.get("case-test-1") == before


def test_odd_order_values_do_not_break_sorting(monkeypatch):
    case = make_case(
        contacts=[
            {"contact_id": "c_anita", "name": "Anita", "order": "second"},
            {"contact_id": "c_rohan", "name": "Rohan", "order": 1},
        ]
    )
    handler = load_handler(monkeypatch, [case])

    response = handler.lambda_handler(escalate(1), None)

    assert response["statusCode"] == 200
    assert "c_anita" in handler.tasks_table.get("case-test-1")["approvals"]


def test_unknown_missing_and_non_string_steps_are_ignored(monkeypatch):
    steps = [
        "SELF_DESTRUCT", "escalate", "expire", " ESCALATE ", "", None,
        123, 1.5, True, ["ESCALATE"], {"step": "EXPIRE"},
    ]

    for step in steps:
        handler = load_handler(monkeypatch, [make_case()])
        before = handler.tasks_table.get("case-test-1")
        event = {"task_id": "case-test-1"}

        if step is not None:
            event["step"] = step

        response = handler.lambda_handler(event, None)

        assert response["statusCode"] == 200, repr(step)
        assert response["result"] == "ignored", repr(step)
        assert response["step"] is None or isinstance(response["step"], str), repr(step)
        assert handler.tasks_table.get("case-test-1") == before, repr(step)
        assert handler.audit_table.types() == ["SCAM_WAKE_IGNORED"], repr(step)


def test_a_very_long_step_is_cut_down_in_the_audit_record(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])

    handler.lambda_handler({"task_id": "case-test-1", "step": "X" * 5000}, None)
    details = handler.audit_table.of_type("SCAM_WAKE_IGNORED")[0]["details"]

    assert len(details["step"]) <= 40


def test_real_aws_errors_are_not_swallowed(monkeypatch):
    # Only a failed CONDITION means 'already handled'. Anything else must
    # raise so EventBridge retries the wake-up.
    from lambda_fakes import client_error

    handler = load_handler(monkeypatch, [make_case()])

    def broken_update(**_kwargs):
        raise client_error("ProvisionedThroughputExceededException")

    monkeypatch.setattr(handler.tasks_table, "update_item", broken_update)

    with pytest.raises(Exception) as caught:
        handler.lambda_handler(escalate(1), None)

    assert "ProvisionedThroughputExceededException" in str(caught.value)

    with pytest.raises(Exception):
        handler.lambda_handler(expire(), None)


# ------------------------------------------------------- never release money


def test_no_step_and_no_status_can_ever_release_a_payment(monkeypatch):
    steps = [
        escalate(1), escalate(2), escalate(0), expire(),
        {"task_id": "case-test-1", "step": "APPROVE"},
        {"task_id": "case-test-1", "step": "RELEASE_PAYMENT"},
        {"task_id": "case-test-1"},
    ]

    for status in ALL_STATUSES:
        for payment in ["HELD", "BLOCKED", "NONE"]:
            for step in steps:
                case = make_case(status=status, payment_status=payment)
                handler = load_handler(monkeypatch, [case])

                handler.lambda_handler(copy.deepcopy(step), None)
                stored = handler.tasks_table.get("case-test-1")

                assert stored["payment_status"] != "RELEASED", (status, payment, step)
                assert stored["approved"] is False, (status, payment, step)
                assert stored["status"] != "APPROVED" or status == "APPROVED", (status, step)


def test_final_cases_are_never_modified_by_any_step(monkeypatch):
    finals = ["CLEARED", "BLOCKED", "APPROVED", "REJECTED", "EXPIRED_BLOCKED"]

    for status in finals:
        for step in [escalate(1), expire()]:
            handler = load_handler(monkeypatch, [make_case(status=status)])
            before = handler.tasks_table.get("case-test-1")

            handler.lambda_handler(copy.deepcopy(step), None)

            assert handler.tasks_table.get("case-test-1") == before, (status, step)


def test_every_scam_wake_up_leaves_a_trace_in_the_audit_log(monkeypatch):
    for step in [escalate(1), expire(), escalate(9), {"task_id": "case-test-1"}]:
        handler = load_handler(monkeypatch, [make_case()])

        handler.lambda_handler(copy.deepcopy(step), None)

        assert handler.audit_table.items, step