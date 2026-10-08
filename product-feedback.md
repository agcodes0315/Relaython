# 💬 Relay Product Feedback

### Feedback from building a durable MCP + AWS agent system

This document summarizes product, SDK and developer-experience feedback gathered while building [Relay](../README.md).

![Services Reviewed](https://img.shields.io/badge/Services%20Reviewed-8-181717?style=flat-square)
![Would Build Again](https://img.shields.io/badge/Would%20Build%20Again-8%2F8-2EA44F?style=flat-square)

`MCP` `Streamable HTTP` `ECS Express` `ECR` `DynamoDB` `EventBridge Scheduler` `Lambda` `Bedrock` `Alexa+`

## 📋 Summary

| Product | Used For | Biggest Improvement Opportunity | Build Again? |
|---|---|---|---|
| MCP Python SDK | Exposing Relay capabilities as tools | Clearer SDK vs protocol version docs | Yes |
| MCP Streamable HTTP | Connecting clients to the public backend | Production security guidance earlier | Yes |
| Amazon ECS Express | Hosting the public MCP container | Clearer view of the active deployment state | Yes |
| Amazon ECR | Versioned image storage | Windows credential-helper fallback docs | Yes |
| Amazon DynamoDB | Durable task state and audit trail | More durable-workflow examples for agents | Yes |
| Amazon EventBridge Scheduler | One-time future wake-ups | Clearer IAM relationships | Yes |
| AWS Lambda | Resume worker | Easier artifact hash verification | Yes |
| Amazon Bedrock / Mantle | Optional orchestration layer | Model vs deterministic policy guidance | Yes |

The Alexa+ Developer Console was also reviewed (see below).

---

## 🔌 MCP Python SDK

### What I Used It For

Relay exposes task-delegation capabilities through MCP tools using Streamable HTTP.

The MCP server handles:

- task creation
- provider search
- option proposal
- provider selection
- explicit approval
- audit retrieval
- failure recovery
- provider restoration
- durable scheduling

### What Worked Well

MCP maps naturally to agent systems because every capability becomes an explicit tool rather than one large opaque agent endpoint.

It also allowed the same backend to be used by:

- Python tests
- the Node bridge
- the simulated Alexa+ frontend

### What Needs Improvement

SDK migration and version differences were initially confusing.

The distinction between the **SDK version** and the **MCP protocol version** should be clearer in beginner documentation.

### Would I Build With It Again?

**Yes.**

MCP was one of the strongest architectural choices in Relay because it made capabilities inspectable and independently testable.

---

## 🌐 MCP Streamable HTTP

### What I Used It For

Connecting the client experience to the public Relay MCP backend.

### What Worked Well

The same service could be exercised through multiple clients while keeping the durable backend independent from the UI.

### What Needs Improvement

Production security guidance should appear earlier.

Developers should be prompted to think about the following before moving a development server to the internet:

- authentication
- authorization
- Host validation
- Origin validation
- public endpoint exposure

### Would I Build With It Again?

**Yes**, with authentication and Host/Origin validation included from the beginning.

---

## ☁️ Amazon ECS Express

### What I Used It For

Hosting the public Relay MCP container.

### What Worked Well

It provided a stable HTTPS endpoint and integrated naturally with:

- ECR
- DynamoDB
- EventBridge Scheduler
- Lambda
- IAM

### What Needs Improvement

The active deployment state can be difficult to reason about during rapid iteration.

A summary showing the following would make debugging easier:

```text
image URI
image digest
task definition revision
active service revision
```

### Would I Build With It Again?

**Yes.**

---

## 📦 Amazon ECR

### What I Used It For

Versioned storage of Relay MCP images.

### What Worked Well

Immutable image tags created reliable deployment checkpoints.

```text
recovery-v1
recovery-v2
resume-v1
secure-v1
```

### What Needs Improvement

Docker Desktop credential-helper behavior on Windows caused avoidable friction.

A documented fallback using an isolated temporary Docker config would help.

### Would I Build With It Again?

**Yes.**

---

## 🗃️ Amazon DynamoDB

### What I Used It For

Relay uses two tables:

| Table | Purpose |
|---|---|
| `RelayTasks` | Durable workflow state |
| `RelayAudit` | Append-only decision events |

### What Worked Well

DynamoDB was a strong fit for durable workflow state.

It allowed the same task to be accessed by:

- MCP tools
- recovery logic
- the resume Lambda

The audit table also made it easy to build decision receipts.

### What Needs Improvement

Agent tutorials could include more examples of durable workflow state rather than focusing primarily on chat or session memory.

### Would I Build With It Again?

**Yes.**

DynamoDB was central to demonstrating that Relay is a durable agent rather than only a conversational interface.

---

## ⏰ Amazon EventBridge Scheduler

### What I Used It For

Creating one-time future wake-ups for Relay tasks.

### What Worked Well

It provided a clean workflow without requiring a continuously running worker:

```text
persist now → wake later
```

### What Needs Improvement

The IAM relationship between the following is not immediately obvious to a first-time user:

- ECS task role
- EventBridge Scheduler
- Scheduler execution role
- Lambda

### Would I Build With It Again?

**Yes.**

It is a strong building block for long-running agent workflows.

---

## ⚡ AWS Lambda

### What I Used It For

`RelayResumeWorker` reloads durable task state and records:

```text
RESUME_TRIGGERED
STATE_RESTORED
TASK_RESUMED
```

### What Worked Well

Lambda is a natural runtime for short durable wake-up work.

It proved that the task could continue without depending on an in-memory timer in the frontend or the MCP container.

### What Needs Improvement

Artifact verification during CLI deployments could be easier.

A clear comparison between the **local artifact hash** and the **deployed Lambda hash** would improve debugging.

### Would I Build With It Again?

**Yes.**

---

## 🤖 Amazon Bedrock / Bedrock Mantle

### What I Used It For

Relay includes an optional agent-orchestration layer backed by the Bedrock Mantle OpenAI-compatible endpoint.

Default model:

```text
openai.gpt-oss-20b
```

### What Worked Well

The OpenAI-compatible interface made it straightforward to implement a tool-calling loop.

The model can help with:

- request interpretation
- tool orchestration
- conversational explanation
- summarizing tool results

### What Needs Improvement

Agent examples should emphasize the separation between **model reasoning** and **deterministic policy**.

A model should not be the only layer enforcing:

- spend limits
- irreversible actions
- authorization
- workflow state transitions

### Would I Build With It Again?

**Yes**, as an orchestration layer around deterministic controls.

---

## 🗣️ Alexa+ Developer Experience

### What I Used It For

Relay was designed as an Alexa+-style delegated task experience.

### What Worked Well

The interaction model fits Relay's core idea:

```text
delegate an outcome instead of micromanaging every step
```

### What Needs Improvement

The available Alexa+ Developer Console showed a **Coming Soon** experience, preventing direct integration during the hackathon.

Because of that, Relay uses a clearly labeled simulated Alexa+ web interface connected to the real MCP backend.

A broadly available developer sandbox would make end-to-end testing significantly easier.

### Would I Build With It Again?

**Yes.**

Relay's MCP backend was intentionally designed so the client surface can change without rewriting the durable workflow layer.

---

## 🧩 Overall Product Feedback

The AWS services used in Relay fit together naturally:

```text
Alexa+-style Client
        |
       MCP
        |
   ECS Express
        |
    DynamoDB
        |
EventBridge Scheduler
        |
      Lambda
        |
    DynamoDB
```

The strongest improvement opportunity is a first-party reference architecture that combines:

- durable state
- scheduling
- human approval
- authentication
- auditability
- failure recovery
- agent tooling

The central lesson from Relay is that the hardest part of agentic software is not only choosing the next action.

It is safely carrying user intent across:

```text
time
services
failures
approvals
retries
```

without losing the original task contract.

---

[← Back to README](../README.md) · [← Friction log](./friction-log.md)