from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Callable


@dataclass(frozen=True)
class IdempotencyDecision:
    key: str
    duplicate: bool
    result: Any = None


def canonical_key(operation: str, task_id: str, payload: dict[str, Any] | None = None) -> str:
    body = {"operation": operation, "task_id": task_id, "payload": payload or {}}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._values: dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self._values.get(key)

    def put_if_absent(self, key: str, value: Any) -> bool:
        if key in self._values:
            return False
        self._values[key] = value
        return True


def execute_idempotently(
    *,
    operation: str,
    task_id: str,
    payload: dict[str, Any] | None,
    store: InMemoryIdempotencyStore,
    fn: Callable[[], Any],
) -> IdempotencyDecision:
    key = canonical_key(operation, task_id, payload)
    cached = store.get(key)

    if cached is not None:
        return IdempotencyDecision(key, True, cached)

    result = fn()

    if not store.put_if_absent(key, result):
        return IdempotencyDecision(key, True, store.get(key))

    return IdempotencyDecision(key, False, result)
