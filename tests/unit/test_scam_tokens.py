from __future__ import annotations

from datetime import datetime, timezone

from relay.scam.tokens import (
    code_expiry,
    is_expired,
    make_token,
    verify_token,
)


SECRET = "test-secret-for-relay-shield"
CASE_ID = "case-123"
CONTACT_ID = "c_rohan"
ISSUED_AT = "2026-10-14T10:00:00+00:00"


def test_same_inputs_create_same_code():
    first = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    second = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    assert first == second


def test_code_is_exactly_eight_characters():
    code = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    assert len(code) == 8


def test_code_uses_base32_alphabet():
    code = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")

    assert all(character in allowed for character in code)


def test_changing_case_id_changes_code():
    first = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    second = make_token(
        SECRET,
        "case-456",
        CONTACT_ID,
        ISSUED_AT,
    )

    assert first != second


def test_changing_contact_id_changes_code():
    first = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    second = make_token(
        SECRET,
        CASE_ID,
        "c_anita",
        ISSUED_AT,
    )

    assert first != second


def test_changing_issued_at_changes_code():
    first = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    second = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        "2026-10-14T10:01:00+00:00",
    )

    assert first != second


def test_correct_code_verifies():
    code = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    assert verify_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
        code,
    )


def test_lowercase_code_verifies():
    code = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    assert verify_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
        code.lower(),
    )


def test_spaced_and_dashed_code_verifies():
    code = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    formatted = f"{code[:4]}-{code[4:]}"

    assert verify_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
        formatted,
    )


def test_wrong_code_fails():
    assert not verify_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
        "AAAAAAAA",
    )


def test_empty_code_fails():
    assert not verify_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
        "",
    )


def test_none_code_fails():
    assert not verify_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
        None,
    )


def test_wrong_length_code_fails():
    assert not verify_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
        "ABC123",
    )


def test_code_expiry_adds_exact_minutes():
    result = code_expiry(
        "2026-10-14T10:00:00+00:00",
        30,
    )

    assert result == "2026-10-14T10:30:00+00:00"


def test_not_expired_one_second_before_boundary():
    expires_at = "2026-10-14T10:30:00+00:00"
    now = "2026-10-14T10:29:59+00:00"

    assert is_expired(expires_at, now) is False


def test_expired_exactly_at_boundary():
    expires_at = "2026-10-14T10:30:00+00:00"
    now = "2026-10-14T10:30:00+00:00"

    assert is_expired(expires_at, now) is True


def test_expired_after_boundary():
    expires_at = "2026-10-14T10:30:00+00:00"
    now = "2026-10-14T10:30:01+00:00"

    assert is_expired(expires_at, now) is True


def test_naive_timestamp_is_rejected():
    try:
        code_expiry(
            "2026-10-14T10:00:00",
            30,
        )
    except ValueError as exc:
        assert "timezone" in str(exc).lower()
    else:
        raise AssertionError("Naive timestamp should raise ValueError")