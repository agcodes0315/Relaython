from __future__ import annotations

import asyncio
import os
import statistics
import time
from dataclasses import dataclass

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


DEFAULT_MCP_URL = (
    "https://re-4f589c522a0645c5b9f2ead60f3e7516."
    "ecs.us-west-2.on.aws/mcp"
)

MCP_URL = os.environ.get("RELAY_MCP_URL", DEFAULT_MCP_URL)
HEALTH_URL = os.environ.get(
    "RELAY_HEALTH_URL",
    MCP_URL.removesuffix("/mcp") + "/health",
)
RUNS = int(os.environ.get("RELAY_BENCH_RUNS", "10"))
TASK_ID = os.environ.get("RELAY_BENCH_TASK_ID")


@dataclass
class Metric:
    name: str
    values_ms: list[float]


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * pct
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def summarize(metric: Metric) -> dict:
    values = metric.values_ms
    return {
        "name": metric.name,
        "runs": len(values),
        "median_ms": statistics.median(values) if values else 0.0,
        "p95_ms": percentile(values, 0.95),
        "min_ms": min(values) if values else 0.0,
        "max_ms": max(values) if values else 0.0,
    }


async def measure_health() -> Metric:
    values = []
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for _ in range(RUNS):
            started = time.perf_counter()
            response = await client.get(HEALTH_URL)
            response.raise_for_status()
            values.append((time.perf_counter() - started) * 1000)
    return Metric("health", values)


async def measure_initialize() -> Metric:
    values = []

    for _ in range(RUNS):
        context = streamable_http_client(MCP_URL)
        streams = await context.__aenter__()
        read_stream, write_stream = streams[0], streams[1]

        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()

        try:
            started = time.perf_counter()
            await session.initialize()
            values.append((time.perf_counter() - started) * 1000)
        finally:
            await session.__aexit__(None, None, None)
            await context.__aexit__(None, None, None)

    return Metric("mcp_initialize", values)


async def measure_session_calls() -> list[Metric]:
    tools_values = []
    risk_values = []
    task_values = []

    context = streamable_http_client(MCP_URL)
    streams = await context.__aenter__()
    read_stream, write_stream = streams[0], streams[1]

    session = ClientSession(read_stream, write_stream)
    await session.__aenter__()

    try:
        await session.initialize()

        for _ in range(RUNS):
            started = time.perf_counter()
            await session.list_tools()
            tools_values.append((time.perf_counter() - started) * 1000)

        for _ in range(RUNS):
            started = time.perf_counter()
            result = await session.call_tool(
                "assess_action_risk",
                {"action": "BOOK"},
            )
            if getattr(result, "isError", False):
                raise RuntimeError("assess_action_risk returned an MCP error")
            risk_values.append((time.perf_counter() - started) * 1000)

        if TASK_ID:
            for _ in range(RUNS):
                started = time.perf_counter()
                result = await session.call_tool(
                    "get_errand",
                    {"task_id": TASK_ID},
                )
                if getattr(result, "isError", False):
                    raise RuntimeError("get_errand returned an MCP error")
                task_values.append((time.perf_counter() - started) * 1000)

    finally:
        await session.__aexit__(None, None, None)
        await context.__aexit__(None, None, None)

    metrics = [
        Metric("tools_list", tools_values),
        Metric("assess_action_risk", risk_values),
    ]

    if task_values:
        metrics.append(Metric("get_errand", task_values))

    return metrics


def print_report(metrics: list[Metric]) -> None:
    print()
    print("Relay MCP Latency Benchmark")
    print("=" * 72)
    print(f"MCP URL: {MCP_URL}")
    print(f"Runs per metric: {RUNS}")
    print()
    print(
        f"{'Metric':24}"
        f"{'Median':>12}"
        f"{'p95':>12}"
        f"{'Min':>12}"
        f"{'Max':>12}"
    )
    print("-" * 72)

    for metric in metrics:
        data = summarize(metric)
        print(
            f"{data['name']:24}"
            f"{data['median_ms']:>10.1f}ms"
            f"{data['p95_ms']:>10.1f}ms"
            f"{data['min_ms']:>10.1f}ms"
            f"{data['max_ms']:>10.1f}ms"
        )

    print()
    print("Alexa+ target: < 500 ms round-trip query response latency.")

    query_metrics = [
        metric
        for metric in metrics
        if metric.name not in {"health", "mcp_initialize"}
    ]

    if query_metrics:
        worst_p95 = max(summarize(metric)["p95_ms"] for metric in query_metrics)
        status = "PASS" if worst_p95 < 500 else "NEEDS IMPROVEMENT"
        print(
            f"Observed query p95 status: {status} "
            f"(worst p95 {worst_p95:.1f} ms)"
        )

    if not TASK_ID:
        print()
        print("Tip: set RELAY_BENCH_TASK_ID to benchmark get_errand.")


async def main() -> None:
    metrics = [await measure_health(), await measure_initialize()]
    metrics.extend(await measure_session_calls())
    print_report(metrics)


if __name__ == "__main__":
    asyncio.run(main())
