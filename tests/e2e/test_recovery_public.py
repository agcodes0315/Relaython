import asyncio
import json

from mcp.client.session import ClientSession
from mcp.client.streamable_http import (
    streamable_http_client,
)


MCP_URL = (
    "https://"
    "re-4f589c522a0645c5b9f2ead60f3e7516."
    "ecs.us-west-2.on.aws/mcp"
)


async def call_tool(
    session,
    name,
    arguments,
):
    print()
    print("=" * 70)
    print("CALLING:", name)

    result = await session.call_tool(
        name,
        arguments,
    )

    texts = []

    for item in result.content:
        if hasattr(item, "text"):
            print(item.text)
            texts.append(item.text)

    if result.is_error:
        raise RuntimeError(
            f"{name} failed."
        )

    if not texts:
        return None

    if len(texts) == 1:
        try:
            return json.loads(
                texts[0]
            )
        except json.JSONDecodeError:
            return texts[0]

    parsed = []

    for text in texts:
        try:
            parsed.append(
                json.loads(text)
            )
        except json.JSONDecodeError:
            parsed.append(text)

    return parsed


async def main():
    print()
    print(
        "PUBLIC RELAY FAILURE "
        "RECOVERY TEST"
    )

    async with streamable_http_client(
        MCP_URL
    ) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            init = (
                await session.initialize()
            )

            print(
                "Protocol:",
                init.protocol_version,
            )

            tools = (
                await session.list_tools()
            )

            print()
            print("Available tools:")

            for tool in tools.tools:
                print("-", tool.name)

            tool_names = {
                tool.name
                for tool in tools.tools
            }

            required = {
                "simulate_provider_failure_tool",
                "restore_provider",
            }

            missing = (
                required - tool_names
            )

            if missing:
                raise RuntimeError(
                    "Recovery tools missing: "
                    + ", ".join(
                        sorted(missing)
                    )
                )

            created = await call_tool(
                session,
                "create_errand",
                {
                    "goal": (
                        "Get my AC serviced"
                    ),
                    "budget": 2000,
                    "deadline": (
                        "2026-10-10"
                    ),
                    "excluded_days": [
                        "Thursday"
                    ],
                },
            )

            task_id = created[
                "task_id"
            ]

            await call_tool(
                session,
                "find_providers",
                {
                    "task_id": task_id,
                },
            )

            await call_tool(
                session,
                "propose_options",
                {
                    "task_id": task_id,
                },
            )

            await call_tool(
                session,
                "select_provider",
                {
                    "task_id": task_id,
                    "provider_id": (
                        "provider_2"
                    ),
                },
            )

            await call_tool(
                session,
                "approve_booking",
                {
                    "task_id": task_id,
                    "approve": True,
                },
            )

            print()
            print(
                "QuickFix approved."
            )
            print(
                "Now simulating "
                "provider failure..."
            )

            recovery = await call_tool(
                session,
                "simulate_provider_failure_tool",
                {
                    "task_id": task_id,
                },
            )

            if (
                recovery["status"]
                != "PROVIDERS_FOUND"
            ):
                raise RuntimeError(
                    "Task did not reopen "
                    "after failure."
                )

            remaining = (
                recovery[
                    "remaining_providers"
                ]
            )

            remaining_ids = {
                provider[
                    "provider_id"
                ]
                for provider in remaining
            }

            if (
                "provider_1"
                not in remaining_ids
            ):
                raise RuntimeError(
                    "CoolCare was not "
                    "available for recovery."
                )

            if (
                "provider_2"
                in remaining_ids
            ):
                raise RuntimeError(
                    "Failed QuickFix "
                    "was offered again."
                )

            await call_tool(
                session,
                "propose_options",
                {
                    "task_id": task_id,
                },
            )

            await call_tool(
                session,
                "select_provider",
                {
                    "task_id": task_id,
                    "provider_id": (
                        "provider_1"
                    ),
                },
            )

            await call_tool(
                session,
                "approve_booking",
                {
                    "task_id": task_id,
                    "approve": True,
                },
            )

            final_task = (
                await call_tool(
                    session,
                    "get_errand",
                    {
                        "task_id": task_id,
                    },
                )
            )

            if (
                final_task[
                    "selected_provider"
                ][
                    "provider_id"
                ]
                != "provider_1"
            ):
                raise RuntimeError(
                    "Recovered provider "
                    "was not selected."
                )

            if not final_task[
                "approved"
            ]:
                raise RuntimeError(
                    "Recovered booking "
                    "was not approved."
                )

            audit = await call_tool(
                session,
                "get_audit_log",
                {
                    "task_id": task_id,
                },
            )

            audit_events = (
                audit
                if isinstance(
                    audit,
                    list,
                )
                else []
            )

            event_types = {
                event.get(
                    "event_type"
                )
                for event
                in audit_events
                if isinstance(
                    event,
                    dict,
                )
            }

            if (
                "PROVIDER_FAILED"
                not in event_types
            ):
                raise RuntimeError(
                    "PROVIDER_FAILED "
                    "missing from audit."
                )

            if (
                "RECOVERY_STARTED"
                not in event_types
            ):
                raise RuntimeError(
                    "RECOVERY_STARTED "
                    "missing from audit."
                )

            await call_tool(
                session,
                "restore_provider",
                {
                    "provider_id": (
                        "provider_2"
                    ),
                },
            )

            print()
            print("=" * 70)
            print(
                "PUBLIC RELAY FAILURE "
                "RECOVERY TEST PASSED"
            )
            print(
                "TASK ID:",
                task_id,
            )
            print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())