from __future__ import annotations

import asyncio
import json
import os
import traceback

from mcp.client.session import ClientSession
from mcp.client.streamable_http import (
    streamable_http_client,
)


DEFAULT_MCP_URL = (
    "https://"
    "re-4f589c522a0645c5b9f2ead60f3e7516."
    "ecs.us-west-2.on.aws/mcp"
)

MCP_URL = os.getenv(
    "RELAY_MCP_URL",
    DEFAULT_MCP_URL,
)

OWNER_ID = "user_savita"


def passed(message: str) -> None:
    print(f"PASS: {message}")


async def call_tool(
    session: ClientSession,
    name: str,
    arguments: dict,
):
    result = await session.call_tool(
        name,
        arguments,
    )

    if result.is_error:
        raise RuntimeError(
            f"{name} returned an MCP error"
        )

    text_items = [
        item.text
        for item in result.content
        if hasattr(item, "text")
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

    for item in text_items:
        try:
            parsed.append(
                json.loads(item)
            )
        except json.JSONDecodeError:
            parsed.append(item)

    return parsed


def contains_code(
    value,
    codes: list[str],
) -> bool:
    rendered = json.dumps(
        value,
        default=str,
    )

    return any(
        code
        and code in rendered
        for code in codes
    )


async def main() -> None:
    print("=" * 70)
    print("PUBLIC RELAY SHIELD END-TO-END TEST")
    print("=" * 70)
    print("Endpoint:", MCP_URL)

    non_inbox_results: list[
        tuple[str, object]
    ] = []

    approval_codes: list[str] = []

    try:
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
                init = await session.initialize()

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

                required = {
                    "analyze_message",
                    "check_number",
                    "assess_scam_risk",
                    "open_protection_case",
                    "get_family_inbox",
                    "record_family_decision",
                    "get_protection_case",
                    "get_case_receipt",
                }

                missing = required - names

                if missing:
                    raise RuntimeError(
                        "Missing Relay Shield tools: "
                        + ", ".join(
                            sorted(missing)
                        )
                    )

                passed(
                    "public MCP exposes Relay Shield tools"
                )

                message = (
                    "Your electricity connection "
                    "will be disconnected today. "
                    "Call immediately and pay "
                    "Rs 25000 to avoid suspension."
                )

                analysis = await call_tool(
                    session,
                    "analyze_message",
                    {
                        "text": message,
                        "sender": None,
                    },
                )

                non_inbox_results.append(
                    (
                        "analyze_message",
                        analysis,
                    )
                )

                assert isinstance(
                    analysis,
                    dict,
                ), analysis

                assert (
                    analysis.get(
                        "risk_score",
                        0,
                    )
                    >= 40
                ), analysis

                passed(
                    "suspicious message analyzed"
                )

                number = await call_tool(
                    session,
                    "check_number",
                    {
                        "number": "9000000001",
                    },
                )

                non_inbox_results.append(
                    (
                        "check_number",
                        number,
                    )
                )

                assert isinstance(
                    number,
                    dict,
                ), number

                passed(
                    "synthetic number reputation checked"
                )

                risk_score = max(
                    85,
                    int(
                        analysis.get(
                            "risk_score",
                            0,
                        )
                    ),
                )

                assessed = await call_tool(
                    session,
                    "assess_scam_risk",
                    {
                        "owner_id": OWNER_ID,
                        "risk_score": risk_score,
                        "amount": 25000,
                        "payee_is_new": True,
                    },
                )

                non_inbox_results.append(
                    (
                        "assess_scam_risk",
                        assessed,
                    )
                )

                assert (
                    assessed.get("decision")
                    == "HOLD"
                ), assessed

                passed(
                    "payment policy returned HOLD"
                )

                opened = await call_tool(
                    session,
                    "open_protection_case",
                    {
                        "owner_id": OWNER_ID,
                        "risk_score": risk_score,
                        "amount": 25000,
                        "payee_label": (
                            "New electricity payee"
                        ),
                        "payee_is_new": True,
                        "signals": [
                            "threat",
                            "payment_demand",
                            "urgency",
                        ],
                        "cooling_off_minutes": 2,
                    },
                )

                non_inbox_results.append(
                    (
                        "open_protection_case",
                        opened,
                    )
                )

                case_id = (
                    opened.get("task_id")
                    or opened.get("case_id")
                )

                if not case_id:
                    raise AssertionError(
                        "Protection case returned "
                        "no case identifier"
                    )

                assert (
                    opened.get("status")
                    == "AWAITING_FAMILY"
                ), opened

                passed(
                    "protection case opened and payment held"
                )

                rohan_inbox = None

                for attempt in range(
                    1,
                    7,
                ):
                    rohan_inbox = (
                        await call_tool(
                            session,
                            "get_family_inbox",
                            {
                                "case_id": case_id,
                                "contact_id": (
                                    "c_rohan"
                                ),
                            },
                        )
                    )

                    if (
                        isinstance(
                            rohan_inbox,
                            dict,
                        )
                        and rohan_inbox.get(
                            "found"
                        )
                    ):
                        break

                    print(
                        "Waiting for Rohan "
                        f"family alert "
                        f"({attempt}/6)..."
                    )

                    await asyncio.sleep(3)

                assert (
                    rohan_inbox
                    and rohan_inbox.get(
                        "found"
                    )
                ), rohan_inbox

                rohan_code = (
                    rohan_inbox.get(
                        "approval_code"
                    )
                )

                assert rohan_code

                approval_codes.append(
                    rohan_code
                )

                # Never print the code itself.
                passed(
                    "Rohan received a private approval code"
                )

                print()
                print(
                    "Waiting for the real EventBridge "
                    "escalation to Anita..."
                )

                anita_inbox = None

                # Two-minute demo mode schedules the
                # escalation around the one-minute mark.
                # Allow 150 seconds of slack.
                for elapsed in range(
                    0,
                    151,
                    10,
                ):
                    anita_inbox = (
                        await call_tool(
                            session,
                            "get_family_inbox",
                            {
                                "case_id": case_id,
                                "contact_id": (
                                    "c_anita"
                                ),
                            },
                        )
                    )

                    if (
                        isinstance(
                            anita_inbox,
                            dict,
                        )
                        and anita_inbox.get(
                            "found"
                        )
                    ):
                        break

                    print(
                        "Escalation pending: "
                        f"{elapsed}s elapsed "
                        "(limit 150s)"
                    )

                    await asyncio.sleep(10)

                assert (
                    anita_inbox
                    and anita_inbox.get(
                        "found"
                    )
                ), (
                    "Anita did not receive the "
                    "escalated family alert within "
                    "150 seconds"
                )
                anita_code = (
                    anita_inbox.get(
                        "approval_code"
                    )
                )

                assert anita_code

                approval_codes.append(
                    anita_code
                )

                assert (
                    anita_code
                    != rohan_code
                )

                passed(
                    "EventBridge/Lambda escalated the case to Anita"
                )

                rejected = await call_tool(
                    session,
                    "record_family_decision",
                    {
                        "case_id": case_id,
                        "contact_id": (
                            "c_anita"
                        ),
                        "approval_code": (
                            anita_code
                        ),
                        "decision": "REJECT",
                    },
                )

                non_inbox_results.append(
                    (
                        "record_family_decision",
                        rejected,
                    )
                )
                assert (
                    rejected.get("status")
                    == "REJECTED"
                ), rejected

                passed(
                    "Anita rejected the payment"
                )
                final_case = await call_tool(
                    session,
                    "get_protection_case",
                    {
                        "case_id": case_id,
                        "owner_id": OWNER_ID,
                    },
                )

                non_inbox_results.append(
                    (
                        "get_protection_case",
                        final_case,
                    )
                )

                assert (
                    final_case.get("status")
                    == "REJECTED"
                ), final_case

                assert (
                    final_case.get(
                        "payment_status"
                    )
                    == "BLOCKED"
                ), final_case

                passed(
                    "final case is REJECTED / BLOCKED"
                )

                receipt = await call_tool(
                    session,
                    "get_case_receipt",
                    {
                        "case_id": case_id,
                        "owner_id": OWNER_ID,
                    },
                )

                non_inbox_results.append(
                    (
                        "get_case_receipt",
                        receipt,
                    )
                )

                assert isinstance(
                    receipt,
                    dict,
                ), receipt

                passed(
                    "auditable case receipt returned"
                )

                for (
                    tool_name,
                    result,
                ) in non_inbox_results:
                    if contains_code(
                        result,
                        approval_codes,
                    ):
                        raise AssertionError(
                            "Approval code leaked from "
                            f"{tool_name}"
                        )

                passed(
                    "approval codes appeared only in family inbox responses"
                )
                print()
                print("=" * 70)
                print(
                    "PUBLIC RELAY SHIELD "
                    "END-TO-END TEST PASSED"
                )
                print("=" * 70)
    except Exception:
        print()
        print(
            "FAIL: Public Relay Shield "
            "end-to-end test"
        )
        traceback.print_exc()
        raise
if __name__ == "__main__":
    asyncio.run(main())