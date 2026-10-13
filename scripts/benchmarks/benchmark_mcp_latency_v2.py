from __future__ import annotations
import asyncio, os, statistics, time
from dataclasses import dataclass
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

DEFAULT_MCP_URL = "https://re-4f589c522a0645c5b9f2ead60f3e7516.ecs.us-west-2.on.aws/mcp"
MCP_URL = os.environ.get("RELAY_MCP_URL", DEFAULT_MCP_URL)
HEALTH_URL = os.environ.get("RELAY_HEALTH_URL", MCP_URL.removesuffix("/mcp") + "/health")
RUNS = int(os.environ.get("RELAY_BENCH_RUNS", "50"))
WARMUP_RUNS = int(os.environ.get("RELAY_BENCH_WARMUP", "5"))
TASK_ID = os.environ.get("RELAY_BENCH_TASK_ID")

@dataclass
class Metric:
    name: str
    values_ms: list[float]
    include_in_query_target: bool = True

def percentile(values, pct):
    if not values: return 0.0
    ordered = sorted(values)
    index = (len(ordered)-1)*pct
    lo = int(index); hi = min(lo+1, len(ordered)-1)
    return ordered[lo] + (ordered[hi]-ordered[lo])*(index-lo)

def summarize(metric):
    v = metric.values_ms
    return {
        "median": statistics.median(v) if v else 0.0,
        "p95": percentile(v, .95),
        "p99": percentile(v, .99),
        "min": min(v) if v else 0.0,
        "max": max(v) if v else 0.0,
    }

async def measure_health():
    vals=[]
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for _ in range(WARMUP_RUNS):
            r=await client.get(HEALTH_URL); r.raise_for_status()
        for _ in range(RUNS):
            s=time.perf_counter()
            r=await client.get(HEALTH_URL); r.raise_for_status()
            vals.append((time.perf_counter()-s)*1000)
    return Metric("health", vals, False)

async def measure_initialize():
    vals=[]
    for i in range(WARMUP_RUNS+RUNS):
        ctx=streamable_http_client(MCP_URL); streams=await ctx.__aenter__()
        session=ClientSession(streams[0], streams[1]); await session.__aenter__()
        try:
            s=time.perf_counter(); await session.initialize()
            if i>=WARMUP_RUNS: vals.append((time.perf_counter()-s)*1000)
        finally:
            await session.__aexit__(None,None,None); await ctx.__aexit__(None,None,None)
    return Metric("mcp_initialize", vals, False)

async def measure_calls():
    tools=[]; risk=[]; task=[]
    ctx=streamable_http_client(MCP_URL); streams=await ctx.__aenter__()
    session=ClientSession(streams[0], streams[1]); await session.__aenter__()
    try:
        await session.initialize()
        for _ in range(WARMUP_RUNS): await session.list_tools()
        for _ in range(RUNS):
            s=time.perf_counter(); await session.list_tools(); tools.append((time.perf_counter()-s)*1000)
        for _ in range(WARMUP_RUNS):
            await session.call_tool("assess_action_risk", {"action":"BOOK"})
        for _ in range(RUNS):
            s=time.perf_counter()
            r=await session.call_tool("assess_action_risk", {"action":"BOOK"})
            if getattr(r,"isError",False): raise RuntimeError("assess_action_risk failed")
            risk.append((time.perf_counter()-s)*1000)
        if TASK_ID:
            for _ in range(WARMUP_RUNS):
                await session.call_tool("get_errand", {"task_id":TASK_ID})
            for _ in range(RUNS):
                s=time.perf_counter()
                r=await session.call_tool("get_errand", {"task_id":TASK_ID})
                if getattr(r,"isError",False): raise RuntimeError("get_errand failed")
                task.append((time.perf_counter()-s)*1000)
    finally:
        await session.__aexit__(None,None,None); await ctx.__aexit__(None,None,None)
    out=[Metric("tools_list",tools,False), Metric("assess_action_risk",risk,True)]
    if task: out.append(Metric("get_errand",task,True))
    return out

async def main():
    metrics=[await measure_health(), await measure_initialize()]
    metrics.extend(await measure_calls())
    print("\nRelay MCP Latency Benchmark v2")
    print("="*86)
    print(f"Warm-up runs: {WARMUP_RUNS} | Measured runs: {RUNS}\n")
    print(f"{'Metric':24}{'Median':>12}{'p95':>12}{'p99':>12}{'Min':>12}{'Max':>12}")
    print("-"*86)
    for m in metrics:
        d=summarize(m)
        print(f"{m.name:24}{d['median']:>10.1f}ms{d['p95']:>10.1f}ms{d['p99']:>10.1f}ms{d['min']:>10.1f}ms{d['max']:>10.1f}ms")
    q=[m for m in metrics if m.include_in_query_target]
    if q:
        worst=max(summarize(m)["p95"] for m in q)
        print(f"\nRepresentative tool-call p95: {'PASS' if worst<500 else 'NEEDS IMPROVEMENT'} ({worst:.1f} ms)")
    if not TASK_ID:
        print("\nSet RELAY_BENCH_TASK_ID to include get_errand.")

if __name__=="__main__":
    asyncio.run(main())
