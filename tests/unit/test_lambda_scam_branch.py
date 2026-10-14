

from lambda_fakes import (
    ESCALATE_TO_1,
    EXPIRE,
    load_handler,
    make_case,
    make_plain_task,
)


def test_escalate_moves_to_the_next_contact_once(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])

    response = handler.lambda_handler(dict(ESCALATE_TO_1), None)
    case = handler.tasks_table.get("case-test-1")

    assert response == {
        "statusCode": 200,
        "task_id": "case-test-1",
        "step": "ESCALATE",
        "result": "applied",
    }
    assert case["current_contact_index"] == 1
    assert case["status"] == "AWAITING_FAMILY"
    assert "c_anita" in case["approvals"]
    assert case["approvals"]["c_anita"]["used"] is False
    assert case["approvals"]["c_anita"]["attempts"] == 0
    assert case["approvals"]["c_anita"]["expires_at"] == case["hold_expires_at"]
    assert handler.audit_table.types() == ["ESCALATED"]


def test_an_identical_second_escalate_is_skipped(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])

    handler.lambda_handler(dict(ESCALATE_TO_1), None)
    after_first = handler.tasks_table.get("case-test-1")

    second = handler.lambda_handler(dict(ESCALATE_TO_1), None)

    assert second["statusCode"] == 200
    assert second["result"] == "skipped"
    assert handler.tasks_table.get("case-test-1") == after_first
    assert handler.audit_table.types() == ["ESCALATED", "ESCALATE_SKIPPED"]


def test_expire_blocks_the_payment(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])

    response = handler.lambda_handler(dict(EXPIRE), None)
    case = handler.tasks_table.get("case-test-1")

    assert response["result"] == "applied"
    assert case["status"] == "EXPIRED_BLOCKED"
    assert case["payment_status"] == "BLOCKED"
    assert case["approved"] is False
    assert case["decided_at"]
    assert handler.audit_table.types() == ["HOLD_EXPIRED", "PAYMENT_BLOCKED"]


def test_a_non_scam_task_still_returns_the_old_response_shape(monkeypatch):
    handler = load_handler(monkeypatch, [make_plain_task()])

    response = handler.lambda_handler({"task_id": "task-plain-1"}, None)

    assert set(response.keys()) == {
        "statusCode",
        "task_id",
        "task_status",
        "wait_status",
        "resume_count",
        "last_resumed_at",
        "message",
    }
    assert response["statusCode"] == 200
    assert response["task_status"] == "SEARCHING"
    assert response["wait_status"] == "RESUMED"
    assert handler.audit_table.types() == [
        "RESUME_TRIGGERED",
        "STATE_RESTORED",
        "TASK_RESUMED",
    ]


def test_an_unknown_step_is_ignored(monkeypatch):
    handler = load_handler(monkeypatch, [make_case()])
    before = handler.tasks_table.get("case-test-1")

    response = handler.lambda_handler(
        {"task_id": "case-test-1", "step": "SELF_DESTRUCT"},
        None,
    )

    assert response["statusCode"] == 200
    assert response["result"] == "ignored"
    assert handler.tasks_table.get("case-test-1") == before
    assert handler.audit_table.types() == ["SCAM_WAKE_IGNORED"]


def test_a_missing_task_still_returns_the_old_404(monkeypatch):
    handler = load_handler(monkeypatch)

    response = handler.lambda_handler({"task_id": "nope"}, None)

    assert response == {
        "statusCode": 404,
        "task_id": "nope",
        "message": "Relay task not found",
    }


def test_a_missing_task_id_still_returns_the_old_400(monkeypatch):
    handler = load_handler(monkeypatch)

    response = handler.lambda_handler({}, None)

    assert response == {
        "statusCode": 400,
        "message": "task_id is required",
    }