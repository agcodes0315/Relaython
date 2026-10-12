import asyncio
import json

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_URL = (
    "https://re-4f589c522a0645c5b9f2ead60f3e7516."
    "ecs.us-west-2.on.aws/mcp"
)


async def call_tool(session, name, arguments):
    print()
    print("=" * 70)
    print(f"CALLING: {name}")
    print("ARGS:")
    print(json.dumps(arguments, indent=2))

    result = await session.call_tool(
        name,
        arguments,
    )

    print()
    print("RESULT:")

    texts = []

    for item in result.content:
        if hasattr(item, "text"):
            print(item.text)
            texts.append(item.text)

    if result.is_error:
        raise RuntimeError(
            f"Tool {name} failed."
        )

    if not texts:
        return None

    try:
        return json.loads(texts[0])
    except json.JSONDecodeError:
        return texts[0]


async def main():
    print()
    print("PUBLIC RELAY END-TO-END TEST")
    print(MCP_URL)

    async with streamable_http_client(MCP_URL) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            init = await session.initialize()

            print()
            print("MCP CONNECTED")
            print(
                "Protocol:",
                init.protocol_version,
            )

            tools = await session.list_tools()

            print()
            print("Available tools:")

            for tool in tools.tools:
                print("-", tool.name)

            # -------------------------------------------------
            # 1. Create errand
            # -------------------------------------------------

            task = await call_tool(
                session,
                "create_errand",
                {
                    "goal": "Get my AC serviced",
                    "budget": 2000,
                    "deadline": "2026-10-10",
                    "excluded_days": [
                        "Thursday"
                    ],
                },
            )

            task_id = task["task_id"]

            print()
            print("TASK ID:")
            print(task_id)

            # -------------------------------------------------
            # 2. Find valid providers
            # -------------------------------------------------

            providers = await call_tool(
                session,
                "find_providers",
                {
                    "task_id": task_id,
                },
            )

            # -------------------------------------------------
            # 3. Propose options
            # -------------------------------------------------

            options = await call_tool(
                session,
                "propose_options",
                {
                    "task_id": task_id,
                },
            )

            # -------------------------------------------------
            # 4. Select QuickFix
            # -------------------------------------------------

            selected = await call_tool(
                session,
                "select_provider",
                {
                    "task_id": task_id,
                    "provider_id": "provider_2",
                },
            )

            # -------------------------------------------------
            # 5. Approve explicitly
            # -------------------------------------------------

            approved = await call_tool(
                session,
                "approve_booking",
                {
                    "task_id": task_id,
                    "approve": True,
                },
            )

            # -------------------------------------------------
            # 6. Read final task
            # -------------------------------------------------

            final_task = await call_tool(
                session,
                "get_errand",
                {
                    "task_id": task_id,
                },
            )

            # -------------------------------------------------
            # 7. Read audit trail
            # -------------------------------------------------

            audit = await call_tool(
                session,
                "get_audit_log",
                {
                    "task_id": task_id,
                },
            )

            print()
            print("=" * 70)
            print("PUBLIC RELAY END-TO-END TEST PASSED")
            print("TASK ID:", task_id)
            print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())