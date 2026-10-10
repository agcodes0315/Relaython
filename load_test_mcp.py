from __future__ import annotations
import argparse, asyncio, statistics, time
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

DEFAULT_URL="https://re-4f589c522a0645c5b9f2ead60f3e7516.ecs.us-west-2.on.aws/mcp"

def pct(v,p):
    if not v: return 0.0
    a=sorted(v); i=(len(a)-1)*p; lo=int(i); hi=min(lo+1,len(a)-1)
    return a[lo]+(a[hi]-a[lo])*(i-lo)

async def one(url, sem):
    async with sem:
        s=time.perf_counter()
        try:
            ctx=streamable_http_client(url); streams=await ctx.__aenter__()
            session=ClientSession(streams[0],streams[1]); await session.__aenter__()
            try:
                await session.initialize()
                r=await session.call_tool("assess_action_risk",{"action":"BOOK"})
                if getattr(r,"isError",False): raise RuntimeError("tool error")
            finally:
                await session.__aexit__(None,None,None); await ctx.__aexit__(None,None,None)
            return True,(time.perf_counter()-s)*1000,None
        except Exception as e:
            return False,(time.perf_counter()-s)*1000,f"{type(e).__name__}: {e}"

async def main(url, concurrency, requests):
    sem=asyncio.Semaphore(concurrency)
    started=time.perf_counter()
    results=await asyncio.gather(*[one(url,sem) for _ in range(requests)])
    duration=time.perf_counter()-started
    good=[x[1] for x in results if x[0]]
    bad=[x for x in results if not x[0]]
    print("\nRelay MCP Lightweight Load Test")
    print("="*72)
    print(f"Concurrency: {concurrency}")
    print(f"Requests: {requests}")
    print(f"Success: {len(good)}/{requests} ({(len(good)/requests*100):.2f}%)")
    print(f"Throughput: {(len(good)/duration if duration else 0):.2f} successful req/s")
    if good:
        print(f"Median: {statistics.median(good):.1f} ms")
        print(f"p95: {pct(good,.95):.1f} ms")
        print(f"p99: {pct(good,.99):.1f} ms")
        print(f"Max: {max(good):.1f} ms")
    if bad:
        print("\nFirst failures:")
        for x in bad[:5]: print("-",x[2])

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--url",default=DEFAULT_URL)
    p.add_argument("--concurrency",type=int,default=10)
    p.add_argument("--requests",type=int,default=50)
    a=p.parse_args()
    asyncio.run(main(a.url,a.concurrency,a.requests))
