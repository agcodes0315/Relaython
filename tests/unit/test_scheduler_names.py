from relay.scheduler import _schedule_name
def test_old_name_behavior_is_preserved():
    assert (
        _schedule_name("task_123:abc")
        == "relay-resume-task-123-abc"
    )
def test_prefix_is_preserved():
    name = _schedule_name("case-123")

    assert name.startswith(
        "relay-resume-"
    )
def test_suffix_is_added():
    name = _schedule_name(
        "case-123",
        "e1",
    )
    assert name.endswith("-e1")
def test_different_suffixes_create_different_names():
    first = _schedule_name(
        "case-123",
        "e1",
    )

    second = _schedule_name(
        "case-123",
        "expire",
    )

    assert first != second
def test_name_never_exceeds_64_characters():
    name = _schedule_name(
        "x" * 100,
        "e1",
    )
    assert len(name) <= 64
def test_suffix_survives_long_task_id():
    name = _schedule_name(
        "x" * 100,
        "expire",
    )
    assert name.endswith(
        "-expire"
    )

    assert len(name) <= 64
def test_underscores_and_colons_are_replaced():
    name = _schedule_name(
        "case_test:123",
    )

    assert "_" not in name
    assert ":" not in name

    assert name == (
        "relay-resume-case-test-123"
    )