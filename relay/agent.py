import json
from typing import Any

from relay.agent_tools import (
    RELAY_TOOL_DEFINITIONS,
    execute_relay_tool,
    serialize_tool_result,
)
from relay.model_provider import (
    get_bedrock_client,
    get_model_name,
)


RELAY_SYSTEM_PROMPT = """
You are Relay, a safe AI agent for carrying delegated
real-world tasks across multiple steps.

Your job is to make progress toward the user's requested
outcome using the provided Relay tools.

STRICT RULES:

1. For every new errand, call create_errand first.

2. Always use the exact task_id returned by Relay.
   Never invent task IDs.

3. For provider errands, normally follow:
   create_errand -> find_providers -> propose_options.

4. Never invent providers, prices, IDs, dates, weekdays,
   availability or booking status.

5. A provider date may only be stated if that exact date
   appears in Relay tool output.

6. Never calculate or guess an availability date yourself.

7. Respect budget, deadline, excluded days and all
   constraints enforced by Relay.

8. If a deadline is missing or ambiguous, ask the user
   for clarification instead of inventing one.

9. Never claim a booking happened unless Relay explicitly
   confirms it.

10. Spending money or creating a commitment requires
    explicit human approval.

11. You do not have authority to approve bookings.

12. When Relay reaches AWAITING_DECISION, explain only
    the options returned by Relay and ask the user to
    choose.

13. When Relay reaches NEEDS_APPROVAL, explicitly tell
    the user approval is required.

14. Use tools rather than guessing.

15. Relay's deterministic policy engine and state machine
    override model reasoning.

16. Keep responses concise, transparent and auditable.
""".strip()


def _item_value(
    item: Any,
    key: str,
    default: Any = None,
) -> Any:
    if isinstance(item, dict):
        return item.get(
            key,
            default,
        )

    return getattr(
        item,
        key,
        default,
    )


def _extract_function_calls(
    response: Any,
) -> list[dict]:
    calls = []

    output_items = getattr(
        response,
        "output",
        [],
    ) or []

    for item in output_items:
        item_type = _item_value(
            item,
            "type",
        )

        if item_type != "function_call":
            continue

        call_id = _item_value(
            item,
            "call_id",
        )

        if not call_id:
            call_id = _item_value(
                item,
                "id",
            )

        name = _item_value(
            item,
            "name",
        )

        raw_arguments = _item_value(
            item,
            "arguments",
            "{}",
        )

        try:
            arguments = json.loads(
                raw_arguments
            )
        except (
            json.JSONDecodeError,
            TypeError,
        ):
            arguments = {}

        calls.append(
            {
                "call_id": call_id,
                "name": name,
                "arguments": arguments,
            }
        )

    return calls


def _extract_text(
    response: Any,
) -> str:
    output_text = getattr(
        response,
        "output_text",
        "",
    )

    if output_text:
        return output_text.strip()

    return ""


class RelayAgent:
    def __init__(self) -> None:
        self.client = (
            get_bedrock_client()
        )
        self.model = (
            get_model_name()
        )

    def run(
        self,
        user_message: str,
    ) -> str:
        response = (
            self.client.responses.create(
                model=self.model,
                instructions=(
                    RELAY_SYSTEM_PROMPT
                ),
                input=user_message,
                tools=(
                    RELAY_TOOL_DEFINITIONS
                ),
                store=True,
            )
        )

        max_tool_rounds = 10

        for _ in range(
            max_tool_rounds
        ):
            tool_calls = (
                _extract_function_calls(
                    response
                )
            )

            if not tool_calls:
                text = _extract_text(
                    response
                )

                if text:
                    return text

                return (
                    "Relay completed the "
                    "request but returned "
                    "no readable text."
                )

            tool_outputs = []

            for call in tool_calls:
                tool_name = (
                    call["name"]
                )

                arguments = (
                    call["arguments"]
                )

                print()
                print(
                    "[Relay tool call] "
                    f"{tool_name}"
                )

                print(
                    "[Arguments] "
                    + json.dumps(
                        arguments,
                        ensure_ascii=False,
                    )
                )

                try:
                    result = (
                        execute_relay_tool(
                            tool_name=(
                                tool_name
                            ),
                            arguments=(
                                arguments
                            ),
                        )
                    )

                except Exception as exc:
                    result = {
                        "error": (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        )
                    }

                serialized_result = (
                    serialize_tool_result(
                        result
                    )
                )

                print(
                    "[Tool result] "
                    + serialized_result
                )

                tool_outputs.append(
                    {
                        "type": (
                            "function_call_output"
                        ),
                        "call_id": (
                            call["call_id"]
                        ),
                        "output": (
                            serialized_result
                        ),
                    }
                )

            response = (
                self.client.responses.create(
                    model=self.model,
                    instructions=(
                        RELAY_SYSTEM_PROMPT
                    ),
                    previous_response_id=(
                        response.id
                    ),
                    input=tool_outputs,
                    tools=(
                        RELAY_TOOL_DEFINITIONS
                    ),
                    store=True,
                )
            )

        return (
            "Relay stopped because "
            "the maximum tool rounds "
            "were reached."
        )
