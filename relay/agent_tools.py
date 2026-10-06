import json
from typing import Any

from relay.tools import (
    create_errand_logic,
    find_providers_logic,
    get_audit_log_logic,
    get_errand_logic,
    propose_options_logic,
    select_provider_logic,
)


RELAY_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "create_errand",
        "description": (
            "Create a new Relay errand from the user's goal "
            "and constraints. Call this first for a new errand."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "The outcome the user wants.",
                },
                "budget": {
                    "type": "number",
                    "description": "Maximum amount the user will spend.",
                },
                "deadline": {
                    "type": "string",
                    "description": "Deadline in YYYY-MM-DD format.",
                },
                "excluded_days": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Weekdays the user does not want.",
                },
            },
            "required": [
                "goal",
                "budget",
                "deadline",
                "excluded_days",
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_errand",
        "description": "Get the current state of a Relay errand.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string"
                }
            },
            "required": [
                "task_id"
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "find_providers",
        "description": (
            "Find providers satisfying the constraints "
            "stored in an existing Relay task."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string"
                }
            },
            "required": [
                "task_id"
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "propose_options",
        "description": (
            "Compare valid providers for a task and present "
            "useful choices such as cheapest and earliest."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string"
                }
            },
            "required": [
                "task_id"
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "select_provider",
        "description": (
            "Select a provider only after the user has "
            "explicitly chosen that provider. This does "
            "not approve spending or create a booking."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string"
                },
                "provider_id": {
                    "type": "string"
                },
            },
            "required": [
                "task_id",
                "provider_id",
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_audit_log",
        "description": (
            "Get the explainable audit history for "
            "a Relay task."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string"
                }
            },
            "required": [
                "task_id"
            ],
            "additionalProperties": False,
        },
    },
]


def execute_relay_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict | list:

    if tool_name == "create_errand":
        return create_errand_logic(
            goal=arguments["goal"],
            budget=arguments["budget"],
            deadline=arguments["deadline"],
            excluded_days=arguments["excluded_days"],
        )

    if tool_name == "get_errand":
        return get_errand_logic(
            task_id=arguments["task_id"],
        )

    if tool_name == "find_providers":
        return find_providers_logic(
            task_id=arguments["task_id"],
        )

    if tool_name == "propose_options":
        return propose_options_logic(
            task_id=arguments["task_id"],
        )

    if tool_name == "select_provider":
        return select_provider_logic(
            task_id=arguments["task_id"],
            provider_id=arguments["provider_id"],
        )

    if tool_name == "get_audit_log":
        return get_audit_log_logic(
            task_id=arguments["task_id"],
        )

    return {
        "error": f"Relay does not permit tool '{tool_name}'."
    }


def serialize_tool_result(
    result: dict | list,
) -> str:
    return json.dumps(
        result,
        ensure_ascii=False,
        default=str,
    )
