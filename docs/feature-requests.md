# Relay — Feature Requests

## 1. Workflow-aware MCP Inspector
**Priority:** Important

Preserve task context across multi-step Streamable HTTP tool calls, approvals and state transitions.

## 2. First-class approval invalidation
**Priority:** Important

Provide a standard way to scope approval to execution context and invalidate it when provider, price, schedule or other material context changes.

## 3. Durable wait/resume MCP + AWS reference architecture
**Priority:** Important

Publish a reference pattern for persistent state, future wake-up, retries, idempotency and restoration.

## 4. Alexa+ local simulator for self-hosted MCP
**Priority:** Important

Provide a developer-accessible local testing harness before gated production access.

## 5. Protocol-to-SDK field mapping documentation
**Priority:** Nice-to-have

Document language-specific SDK naming next to protocol field names.

## 6. Safety examples separating reasoning from authority
**Priority:** Nice-to-have

Show patterns where a model recommends while deterministic policy and humans remain authoritative for irreversible actions.

## 7. Out-of-band approval for MCP tools
**Priority:** Important

Let a tool request approval from a principal other than the caller, such as an SMS or push message to a verified family member, and return the decision to the server without passing through the model. Relay Shield simulates this with `get_family_inbox`.

## 8. Caller identity and per-client tool visibility in MCP
**Priority:** Important

Let a server know who is calling and show different tools to different clients, so an assistant never sees tools meant only for a family member's device. Today every connected client sees every tool, and Relay Shield relies on a one-time code and tool descriptions.

## 9. A local EventBridge Scheduler that fires schedules
**Priority:** Nice-to-have

Provide a local emulator that stores one-time schedules and invokes the target Lambda when they are due, so durable wait and resume can be tested without an AWS account.

## 10. Conditional-update helpers and reserved-word warnings for DynamoDB
**Priority:** Nice-to-have

Provide a small builder or a clearer error for conditional updates on reserved words and nested attributes, because state machines with two writers rely on them.
