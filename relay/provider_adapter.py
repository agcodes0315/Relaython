from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Protocol


@dataclass(frozen=True)
class ProviderOption:
    provider_id: str
    name: str
    price: int
    service_date: date
    available: bool = True


@dataclass(frozen=True)
class TaskConstraints:
    max_budget: int
    deadline: date
    excluded_weekdays: frozenset[str]


class ProviderAdapter(Protocol):
    def list_options(self, service_type: str) -> list[ProviderOption]:
        ...


class SimulatedProviderAdapter:
    def __init__(self, options: Iterable[ProviderOption]) -> None:
        self._options = list(options)

    def list_options(self, service_type: str) -> list[ProviderOption]:
        return list(self._options)


def validate_option(option: ProviderOption, constraints: TaskConstraints) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if not option.available:
        reasons.append("provider_unavailable")
    if option.price > constraints.max_budget:
        reasons.append("budget_exceeded")
    if option.service_date > constraints.deadline:
        reasons.append("deadline_missed")
    if option.service_date.strftime("%A") in constraints.excluded_weekdays:
        reasons.append("excluded_weekday")

    return len(reasons) == 0, reasons


def compliant_options(options: Iterable[ProviderOption], constraints: TaskConstraints) -> list[ProviderOption]:
    return [option for option in options if validate_option(option, constraints)[0]]
