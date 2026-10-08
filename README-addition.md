## 🧭 Delegation Preflight & Autonomy Policy

Relay now exposes two additional MCP tools:

```text
clarify_delegation
assess_action_risk
```

### Clarification / Elicitation

Before creating a task, Relay can deterministically detect missing required constraints.

Example:

```text
User:
"Get my AC serviced."

Relay preflight:
Missing: budget, deadline

Questions:
"What is the maximum amount Relay may consider?"
"What is the latest acceptable date for this task?"
```

Relay does **not** guess missing values.

### Action Risk / Autonomy Boundary

| Action | Risk | Human Approval |
|---|---|---|
| SEARCH | Low | No |
| PROPOSE | Low | No |
| SELECT | Medium | No |
| BOOK | High | **Yes** |
| SCHEDULE_RESUME | Low | No |

Unknown actions fail safe and require review.

---

## ⚡ MCP Latency Benchmark

Run:

```powershell
python .\benchmark_mcp_latency.py
```

To include a real persisted task lookup:

```powershell
$env:RELAY_BENCH_TASK_ID="YOUR_TASK_ID"
python .\benchmark_mcp_latency.py
```

The script reports median and p95 latency and compares query latency against the Alexa+ target.
