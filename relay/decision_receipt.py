from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def receipt_event(
    event_type: str,
    summary: str,
    *,
    details: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "timestamp": timestamp or now_iso(),
        "summary": summary,
        "details": details or {},
    }


def build_decision_receipt(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = sorted(list(events), key=lambda item: item.get("timestamp", ""))
    return {
        "version": "1",
        "event_count": len(items),
        "events": items,
        "answers": {
            "what_was_understood": "See TASK_CREATED / contract events",
            "what_was_enforced": "See POLICY_EVALUATED / PROVIDERS_FILTERED",
            "who_authorized_spend": "See USER_APPROVED",
            "what_failed": "See PROVIDER_FAILED",
            "how_recovery_happened": "See RECOVERY_STARTED and subsequent filtering",
            "how_resume_happened": "See WAIT_SCHEDULED → RESUME_TRIGGERED → STATE_RESTORED → TASK_RESUMED",
        },
    }
