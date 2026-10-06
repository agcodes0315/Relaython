import asyncio

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    url = "http://127.0.0.1:8001/mcp"

    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            result = await session.initialize()

            print()
            print("DOCKER MCP CONNECTED")
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
            print("DOCKER MCP TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main())