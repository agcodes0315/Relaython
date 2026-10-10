# Relay — Feature Requests

These requests come directly from building and debugging Relay.

---

## 1. Workflow-aware MCP Inspector

**Priority:** Important

### Request
Add a workflow mode to MCP Inspector that can preserve context across a sequence of tool calls.

### Why it matters
Durable agents are rarely validated through one isolated tool call. A developer may need to inspect:

```text
create task
→ select provider
→ approve
→ simulate failure
→ recover
→ schedule
→ resume
```

A workflow view would make state transitions, tool arguments and returned state much easier to debug.

---

## 2. First-class approval invalidation patterns

**Priority:** Important

### Request
Provide standard guidance or primitives for:
- scoped approval,
- approval expiry,
- approval invalidation,
- fresh approval after execution context changes.

### Why it matters
A user approving one provider does not automatically authorize a different provider after failure.

This was one of the most important safety lessons from Relay.

---

## 3. Durable wait/resume reference architecture for MCP + AWS

**Priority:** Important

### Request
Publish a reference architecture for:

```text
MCP tool
→ persist state
→ schedule future execution
→ restore state
→ resume workflow
```

Using:
- ECS
- DynamoDB
- EventBridge Scheduler
- Lambda
- IAM

### Why it matters
The logic is simple, but cross-service IAM and debugging create a large onboarding cost.

---

## 4. Alexa+ local simulator for self-hosted MCP

**Priority:** Important

### Request
Provide a generally available local or browser-based Alexa+-style testing surface for developers using the self-hosted MCP path.

### Why it matters
A developer can build the required MCP backend without private preview tooling, but validating the complete conversational/visual experience would be easier with an official simulator.

---

## 5. Protocol-field vs SDK-field documentation

**Priority:** Nice-to-have

### Request
Show protocol JSON names and language-native SDK names side-by-side.

Example:

```text
Protocol: resourceTemplates
Python:   resource_templates

Protocol: uriTemplate
Python:   uri_template
```

### Why it matters
This reduces avoidable compatibility/debugging friction.

---

## 6. Agent safety examples that separate reasoning from authority

**Priority:** Nice-to-have

### Request
Add reference examples demonstrating:
- model reasoning for flexible planning,
- deterministic enforcement for hard constraints,
- human approval for irreversible commitments.

### Why it matters
This is a useful default pattern for agent systems that can spend money or affect real-world services.
