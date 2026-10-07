import asyncio
import json

from mcp.client.session import (
    ClientSession,
)
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
    result = await session.call_tool(
        name,
        arguments,
    )

    if result.is_error:
        raise RuntimeError(
            f"{name} failed"
        )

    text_items = [
        item.text
        for item in result.content
        if hasattr(
            item,
            "text",
        )
    ]

    if not text_items:
        return None

    if len(text_items) == 1:
        try:
            return json.loads(
                text_items[0]
            )
        except json.JSONDecodeError:
            return text_items[0]

    parsed = []

    for text in text_items:
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
        "PUBLIC RELAY DURABLE "
        "RESUME TEST"
    )

    async with (
        streamable_http_client(
            MCP_URL
        )
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

            names = {
                tool.name
                for tool in tools.tools
            }

            print()
            print("Available tools:")

            for name in sorted(names):
                print("-", name)

            if (
                "schedule_task_resume"
                not in names
            ):
                raise RuntimeError(
                    "schedule_task_resume "
                    "is missing"
                )

            created = (
                await call_tool(
                    session,
                    "create_errand",
                    {
                        "goal": (
                            "Get my AC "
                            "serviced"
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
            )

            task_id = created[
                "task_id"
            ]

            print()
            print(
                "Created task:",
                task_id,
            )

            schedule = (
                await call_tool(
                    session,
                    "schedule_task_resume",
                    {
                        "task_id": (
                            task_id
                        ),
                        "minutes": 2,
                    },
                )
            )

            if schedule.get(
                "error"
            ):
                raise RuntimeError(
                    schedule["error"]
                )

            print()
            print(
                "Resume scheduled for:",
                schedule[
                    "run_at_utc"
                ],
            )

            print()
            print(
                "Waiting for real "
                "EventBridge Scheduler..."
            )

            required_events = {
                "WAIT_SCHEDULED",
                "RESUME_TRIGGERED",
                "STATE_RESTORED",
                "TASK_RESUMED",
            }

            found_events = set()

            for attempt in range(
                1,
                11,
            ):
                print(
                    f"Check {attempt}/10"
                )

                await asyncio.sleep(
                    20
                )

                audit = (
                    await call_tool(
                        session,
                        "get_audit_log",
                        {
                            "task_id": (
                                task_id
                            )
                        },
                    )
                )

                events = (
                    audit
                    if isinstance(
                        audit,
                        list,
                    )
                    else []
                )

                found_events = {
                    event.get(
                        "event_type"
                    )
                    for event in events
                    if isinstance(
                        event,
                        dict,
                    )
                }

                if (
                    required_events
                    <= found_events
                ):
                    break

            missing = (
                required_events
                - found_events
            )

            if missing:
                raise RuntimeError(
                    "Resume audit events "
                    "missing: "
                    + ", ".join(
                        sorted(missing)
                    )
                )

            task = (
                await call_tool(
                    session,
                    "get_errand",
                    {
                        "task_id": task_id
                    },
                )
            )

            if (
                task.get(
                    "wait_status"
                )
                != "RESUMED"
            ):
                raise RuntimeError(
                    "Task did not enter "
                    "RESUMED wait state"
                )

            if (
                task.get(
                    "resume_count",
                    0,
                )
                < 1
            ):
                raise RuntimeError(
                    "resume_count was "
                    "not updated"
                )

            print()
            print(
                "WAIT_SCHEDULED ✓"
            )
            print(
                "RESUME_TRIGGERED ✓"
            )
            print(
                "STATE_RESTORED ✓"
            )
            print(
                "TASK_RESUMED ✓"
            )

            print()
            print(
                "Business status preserved:",
                task.get(
                    "status"
                ),
            )

            print(
                "Resume count:",
                task.get(
                    "resume_count"
                ),
            )

            print()
            print("=" * 70)

            print(
                "PUBLIC RELAY DURABLE "
                "RESUME TEST PASSED"
            )

            print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())