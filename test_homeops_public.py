from __future__ import annotations

import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_URL = (
    "https://re-4f589c522a0645c5b9f2ead60f3e7516."
    "ecs.us-west-2.on.aws/mcp"
)


def line():
    print("=" * 72)


async def main():
    line()
    print("PUBLIC RELAY HOMEOPS MCP VALIDATION")
    print(MCP_URL)
    line()

    async with streamable_http_client(MCP_URL) as streams:
        read_stream = streams[0]
        write_stream = streams[1]

        async with ClientSession(read_stream, write_stream) as session:
            init = await session.initialize()
            protocol = getattr(init, "protocolVersion", None)
            print(f"\nProtocol: {protocol}")

            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            print("\nTOOLS:")
            for name in tool_names:
                print(f"- {name}")

            expected_tools = {
                "list_household_assets",
                "get_household_asset",
                "check_warranty",
                "troubleshoot_home_asset",
                "prepare_service_from_asset",
            }

            missing_tools = expected_tools - set(tool_names)
            if missing_tools:
                raise RuntimeError(
                    f"Missing HomeOps tools: {sorted(missing_tools)}"
                )

            resources_result = await session.list_resources()
            print("\nRESOURCES:")
            for resource in resources_result.resources:
                print(f"- {resource.uri}")

            templates_result = await session.list_resource_templates()
            print("\nRESOURCE TEMPLATES:")
            for template in templates_result.resourceTemplates:
                print(f"- {template.uriTemplate}")

            prompts_result = await session.list_prompts()
            prompt_names = [prompt.name for prompt in prompts_result.prompts]

            print("\nPROMPTS:")
            for name in prompt_names:
                print(f"- {name}")

            if "resolve_home_issue" not in prompt_names:
                raise RuntimeError(
                    "Missing resolve_home_issue prompt"
                )

            line()
            print("CALLING: list_household_assets")
            assets = await session.call_tool(
                "list_household_assets",
                {},
            )
            if getattr(assets, "isError", False):
                raise RuntimeError("list_household_assets failed")
            print(assets)

            line()
            print("CALLING: check_warranty")
            warranty = await session.call_tool(
                "check_warranty",
                {
                    "asset_id": "asset_ac_001",
                    "as_of_date": "2026-10-10",
                },
            )
            if getattr(warranty, "isError", False):
                raise RuntimeError("check_warranty failed")
            print(warranty)

            line()
            print("CALLING: troubleshoot_home_asset")
            troubleshoot = await session.call_tool(
                "troubleshoot_home_asset",
                {
                    "asset_id": "asset_ac_001",
                    "symptoms": "The AC is not cooling properly",
                },
            )
            if getattr(troubleshoot, "isError", False):
                raise RuntimeError("troubleshoot_home_asset failed")
            print(troubleshoot)

            line()
            print("CALLING: prepare_service_from_asset")
            handoff = await session.call_tool(
                "prepare_service_from_asset",
                {
                    "asset_id": "asset_ac_001",
                    "symptoms": "The AC is not cooling properly",
                    "budget": 2000,
                    "deadline": "2026-10-10",
                    "excluded_days": ["Thursday"],
                },
            )
            if getattr(handoff, "isError", False):
                raise RuntimeError("prepare_service_from_asset failed")
            print(handoff)

            line()
            print("READING: relay://home/assets")
            resource = await session.read_resource(
                "relay://home/assets"
            )
            print(resource)

            line()
            print("GETTING PROMPT: resolve_home_issue")
            prompt = await session.get_prompt(
                "resolve_home_issue",
                {
                    "asset_id": "asset_ac_001",
                    "symptoms": "The AC is not cooling properly",
                },
            )
            print(prompt)

    print()
    line()
    print("PUBLIC RELAY HOMEOPS MCP VALIDATION PASSED")
    line()


if __name__ == "__main__":
    asyncio.run(main())
