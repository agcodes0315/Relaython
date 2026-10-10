from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar
import time

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay_seconds: float = 0.25
    multiplier: float = 2.0
    max_delay_seconds: float = 2.0


class ResumeRetriesExhausted(RuntimeError):
    pass


def run_with_bounded_retry(
    fn: Callable[[], T],
    *,
    policy: RetryPolicy = RetryPolicy(),
    retryable: Callable[[Exception], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    if policy.max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    delay = policy.initial_delay_seconds
    last_error: Exception | None = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            if retryable is not None and not retryable(exc):
                raise
            if attempt >= policy.max_attempts:
                break
            sleep(min(delay, policy.max_delay_seconds))
            delay = min(delay * policy.multiplier, policy.max_delay_seconds)

    raise ResumeRetriesExhausted(
        f"resume failed after {policy.max_attempts} attempts"
    ) from last_error
