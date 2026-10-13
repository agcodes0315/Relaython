from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone


def make_token(
    secret: str,
    case_id: str,
    contact_id: str,
    issued_at: str,
) -> str:
    """Create an 8-character approval code derived from case/contact/time.

    The approval code is derived rather than stored, so no approval secret
    needs to sit in the database.
    """
    message = f"{case_id}:{contact_id}:{issued_at}".encode("utf-8")
    key = secret.encode("utf-8")

    digest = hmac.new(key, message, hashlib.sha256).digest()

    token = base64.b32encode(digest).decode("ascii").rstrip("=")

    return token[:8].upper()


def verify_token(
    secret: str,
    case_id: str,
    contact_id: str,
    issued_at: str,
    candidate: str,
) -> bool:
    """Verify a family approval code safely.

    Spaces and dashes are ignored and lowercase input is accepted.
    Invalid input returns False instead of raising.
    """
    if not isinstance(candidate, str):
        return False

    normalized = candidate.replace(" ", "").replace("-", "").upper()

    if len(normalized) != 8:
        return False

    expected = make_token(
        secret=secret,
        case_id=case_id,
        contact_id=contact_id,
        issued_at=issued_at,
    )

    return hmac.compare_digest(expected, normalized)


def _parse_iso_utc(value: str) -> datetime:
    """Parse an ISO timestamp and require timezone information."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if dt.tzinfo is None:
        raise ValueError("Timestamp must include timezone information")

    return dt.astimezone(timezone.utc)


def code_expiry(
    issued_at_iso: str,
    minutes: int,
) -> str:
    """Return the UTC expiry timestamp for approval code."""
    issued_at = _parse_iso_utc(issued_at_iso)

    expires_at = issued_at + timedelta(minutes=minutes)

    return expires_at.isoformat()


def is_expired(
    expires_at_iso: str,
    now_iso: str | None = None,
) -> bool:
    """Return True when the expiry time has been reached or passed."""
    expires_at = _parse_iso_utc(expires_at_iso)

    if now_iso is None:
        now = datetime.now(timezone.utc)
    else:
        now = _parse_iso_utc(now_iso)

    return now >= expires_at