import asyncio
import json

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_URL = (
    "https://re-4f589c522a0645c5b9f2ead60f3e7516."
    "ecs.us-west-2.on.aws/mcp"
)


async def main() -> None:
    print()
    print("Connecting to PUBLIC AWS Relay MCP...")
    print(MCP_URL)
    print()

    async with streamable_http_client(MCP_URL) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            result = await session.initialize()

            print("PUBLIC AWS MCP CONNECTED")
            print(
                "Protocol version:",
                result.protocol_version,
            )

            tools = await session.list_tools()

            print()
            print("Relay MCP tools:")

            for tool in tools.tools:
                print("-", tool.name)

            print()
            print("Calling create_errand on AWS...")

            result = await session.call_tool(
                "create_errand",
                {
                    "goal": "Get my AC serviced",
                    "budget": 2000,
                    "deadline": "2026-10-10",
                    "excluded_days": ["Thursday"],
                },
            )

            print()
            print("CREATE ERRAND RESULT:")

            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text)

            if result.is_error:
                raise RuntimeError(
                    "Public create_errand MCP call failed."
                )

            print()
            print("PUBLIC AWS MCP TOOL CALL PASSED")


if __name__ == "__main__":
    asyncio.run(main())