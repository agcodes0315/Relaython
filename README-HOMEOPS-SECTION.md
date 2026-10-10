## 🏠 Relay HomeOps — Contextual Asset & Warranty Intelligence

Relay HomeOps extends Relay's existing durable delegation workflow without replacing it.

```text
"My AC isn't cooling properly."
        ↓
Home Asset Vault
        ↓
Warranty context
        ↓
Safe troubleshooting
        ↓
Service required?
        ↓
Relay durable delegation
        ↓
Provider discovery
        ↓
Human approval
        ↓
Failure recovery
        ↓
Scheduled resume
        ↓
Decision receipt
```

### Why this matters

Alexa+ handles conversational understanding and routing. Relay owns the service-specific execution state:

- household asset context
- stored purchase and warranty metadata
- conservative troubleshooting boundaries
- delegation constraints
- human approval gates
- provider-failure recovery
- durable scheduled continuation
- auditable decisions

> **Alexa+ understands what the customer needs. Relay makes sure the task survives the real world.**

### New MCP surface

**Tools**
```text
list_household_assets
get_household_asset
check_warranty
troubleshoot_home_asset
prepare_service_from_asset
```

**Resources**
```text
relay://home/assets
relay://home/assets/{asset_id}
```

**Prompt**
```text
resolve_home_issue
```

This deliberately demonstrates MCP **Tools + Resources + Prompts** while preserving Relay's existing deterministic policy engine.

### Demo asset

```text
Product: CoolBreeze Split AC
Model: CB-24X
Purchased: 2026-03-12
Warranty expires: 2027-03-12
Retailer: Amazon
Location: Bedroom
```

All purchase/order/warranty/provider/payment data shown in the hackathon demo is simulated unless explicitly stated otherwise.

### Suggested demo

```text
User:
"Alexa, my AC isn't cooling properly."

Relay:
"I found your CoolBreeze Split AC. Its stored warranty runs through
March 12, 2027. I can walk you through safe basic checks first,
or prepare a service request."
```

If the problem persists:

```text
prepare_service_from_asset
→ create_errand
→ find_providers
→ propose_options
→ select_provider
→ human approval
→ recovery if needed
→ scheduled resume
```
