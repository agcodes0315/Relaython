from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RiskPolicy:
    tier: str
    reversible: bool
    human_approval_required: bool
    explanation: str


ACTION_RISK = {
    "SEARCH": RiskPolicy(
        tier="LOW",
        reversible=True,
        human_approval_required=False,
        explanation="Read-only discovery. Relay may perform this autonomously.",
    ),
    "PROPOSE": RiskPolicy(
        tier="LOW",
        reversible=True,
        human_approval_required=False,
        explanation="Presents options without committing the user.",
    ),
    "SELECT": RiskPolicy(
        tier="MEDIUM",
        reversible=True,
        human_approval_required=False,
        explanation=(
            "Chooses a candidate provider, but does not spend money "
            "or create an external commitment."
        ),
    ),
    "BOOK": RiskPolicy(
        tier="HIGH",
        reversible=False,
        human_approval_required=True,
        explanation=(
            "Creates a financial or external commitment. "
            "Explicit human approval is required."
        ),
    ),
    "SCHEDULE_RESUME": RiskPolicy(
        tier="LOW",
        reversible=True,
        human_approval_required=False,
        explanation=(
            "Schedules Relay to resume its own durable task later. "
            "It does not authorize an external purchase."
        ),
    ),
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def clarify_delegation(
    goal: str | None = None,
    budget: float | int | None = None,
    deadline: str | None = None,
    excluded_days: list[str] | None = None,
) -> dict:
    missing_fields: list[str] = []
    questions: list[str] = []

    clean_goal = _clean_text(goal)
    clean_deadline = _clean_text(deadline)
    clean_excluded_days = [
        _clean_text(day)
        for day in (excluded_days or [])
        if _clean_text(day)
    ]

    if not clean_goal:
        missing_fields.append("goal")
        questions.append("What outcome would you like Relay to complete?")

    normalized_budget = None
    if budget is None:
        missing_fields.append("budget")
        questions.append("What is the maximum amount Relay may consider?")
    else:
        try:
            normalized_budget = float(budget)
            if normalized_budget <= 0:
                normalized_budget = None
                missing_fields.append("budget")
                questions.append(
                    "Please provide a maximum budget greater than zero."
                )
        except (TypeError, ValueError):
            missing_fields.append("budget")
            questions.append("Please provide the maximum budget as a number.")

    if not clean_deadline:
        missing_fields.append("deadline")
        questions.append("What is the latest acceptable date for this task?")

    ready = len(missing_fields) == 0

    return {
        "ready": ready,
        "missing_fields": missing_fields,
        "questions": questions,
        "normalized_contract": {
            "goal": clean_goal or None,
            "budget": normalized_budget,
            "deadline": clean_deadline or None,
            "excluded_days": clean_excluded_days,
        },
        "message": (
            "Delegation contract is ready."
            if ready
            else (
                "Relay needs clarification before creating the task. "
                "Missing values were not guessed."
            )
        ),
    }


def assess_action_risk(action: str) -> dict:
    normalized = _clean_text(action).upper()
    policy = ACTION_RISK.get(normalized)

    if policy is None:
        return {
            "action": normalized or None,
            "known_action": False,
            "tier": "UNKNOWN",
            "reversible": False,
            "human_approval_required": True,
            "explanation": (
                "Unknown actions default to the safer policy: "
                "do not execute without explicit review."
            ),
        }

    return {
        "action": normalized,
        "known_action": True,
        "tier": policy.tier,
        "reversible": policy.reversible,
        "human_approval_required": policy.human_approval_required,
        "explanation": policy.explanation,
    }
