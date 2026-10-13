from __future__ import annotations

import inspect

import pytest

from relay.scam.tokens import (
    code_expiry,
    is_expired,
    make_token,
    verify_token,
)


SECRET = "relay-shield-test-secret"
CASE_ID = "case-001"
CONTACT_ID = "c_rohan"
ISSUED_AT = "2026-10-14T10:00:00+00:00"

BASE32_ALPHABET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")


def test_generated_code_has_exact_format():
    code = make_token(SECRET, CASE_ID, CONTACT_ID, ISSUED_AT)

    assert len(code) == 8
    assert set(code) <= BASE32_ALPHABET


@pytest.mark.parametrize(
    ("secret", "case_id", "contact_id", "issued_at"),
    [
        ("relay-shield-test-secreu", CASE_ID, CONTACT_ID, ISSUED_AT),
        (SECRET, "case-002", CONTACT_ID, ISSUED_AT),
        (SECRET, CASE_ID, "c_anita", ISSUED_AT),
        (SECRET, CASE_ID, CONTACT_ID, "2026-10-14T10:00:01+00:00"),
    ],
)
def test_changing_one_input_changes_code(
    secret,
    case_id,
    contact_id,
    issued_at,
):
    original = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    changed = make_token(
        secret,
        case_id,
        contact_id,
        issued_at,
    )

    assert changed != original


def test_2000_distinct_inputs_produce_2000_distinct_codes():
    codes = {
        make_token(
            SECRET,
            f"case-{index}",
            f"contact-{index}",
            f"2026-10-14T10:{index % 60:02d}:{index % 60:02d}+00:00",
        )
        for index in range(2000)
    }

    assert len(codes) == 2000


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
    ) is True


def test_spaces_dashes_and_lowercase_verify():
    code = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    formatted = f"{code[:2]}-{code[2:4]} {code[4:6]}-{code[6:]}".lower()

    assert verify_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
        formatted,
    ) is True


def test_code_for_another_contact_does_not_verify():
    code = make_token(
        SECRET,
        CASE_ID,
        "c_anita",
        ISSUED_AT,
    )

    assert verify_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
        code,
    ) is False


def test_code_for_another_case_does_not_verify():
    code = make_token(
        SECRET,
        "case-other",
        CONTACT_ID,
        ISSUED_AT,
    )

    assert verify_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
        code,
    ) is False


def test_code_from_another_secret_does_not_verify():
    code = make_token(
        "different-secret",
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
    ) is False


@pytest.mark.parametrize(
    "candidate",
    [
        None,
        123,
        "",
        "A" * 10000,
        "ABCD\x00EFG",
        "नमस्ते",
    ],
)
def test_hostile_candidates_return_false_and_never_raise(candidate):
    assert verify_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
        candidate,
    ) is False


def test_verify_token_uses_compare_digest():
    source = inspect.getsource(verify_token)

    assert "hmac.compare_digest" in source


def test_verify_token_does_not_directly_compare_codes():
    source = inspect.getsource(verify_token)

    assert "expected ==" not in source
    assert "normalized ==" not in source


def test_secret_never_appears_in_generated_code():
    code = make_token(
        SECRET,
        CASE_ID,
        CONTACT_ID,
        ISSUED_AT,
    )

    assert SECRET not in code


def test_code_expiry_adds_exact_minutes():
    expiry = code_expiry(
        "2026-10-14T10:00:00+00:00",
        30,
    )

    assert expiry == "2026-10-14T10:30:00+00:00"


def test_not_expired_one_second_before():
    assert is_expired(
        "2026-10-14T10:30:00+00:00",
        "2026-10-14T10:29:59+00:00",
    ) is False


def test_expired_exactly_at_boundary():
    assert is_expired(
        "2026-10-14T10:30:00+00:00",
        "2026-10-14T10:30:00+00:00",
    ) is True


def test_expired_one_second_after():
    assert is_expired(
        "2026-10-14T10:30:00+00:00",
        "2026-10-14T10:30:01+00:00",
    ) is True


def test_naive_expiry_timestamp_is_rejected():
    with pytest.raises(ValueError):
        is_expired(
            "2026-10-14T10:30:00",
            "2026-10-14T10:29:59+00:00",
        )


def test_naive_now_timestamp_is_rejected():
    with pytest.raises(ValueError):
        is_expired(
            "2026-10-14T10:30:00+00:00",
            "2026-10-14T10:29:59",
        )