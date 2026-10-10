## 📊 Validation & Results

Relay is validated through local policy tests and public end-to-end tests against the deployed MCP service.

- **12 MCP tools** exposed over Streamable HTTP
- **6/6 deterministic safety tests** passing
- public end-to-end delegation flow passing
- public provider-failure recovery flow passing
- real **EventBridge Scheduler → Lambda → DynamoDB** resume flow passing
- recovery revalidates budget, deadline and excluded-day constraints
- previous approval is invalidated after provider failure
- replacement booking requires fresh human approval
- clarification and risk-policy tools exposed in production
- representative remote task-tool calls currently measure in the high-200 ms p95 range

### Latency Benchmark

```powershell
$env:RELAY_BENCH_TASK_ID="YOUR_TASK_ID"
python .\benchmark_mcp_latency_v2.py
```

The benchmark uses warm-up requests and 50 measured samples by default, and reports median, p95 and p99.

> Initialization and `tools/list` are reported separately from representative application tool calls so setup/discovery overhead is not presented as normal task-operation latency.

### Lightweight Load Test

```powershell
python .\load_test_mcp.py --concurrency 10 --requests 50
```

Optional second run:

```powershell
python .\load_test_mcp.py --concurrency 25 --requests 100
```

Publish only measured success-rate, throughput and latency results.
