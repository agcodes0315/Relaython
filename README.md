# 🔁 Relay

## The execution layer that helps Alexa+ tasks survive the real world.

> **Assistants are good at starting tasks. Relay is built for what happens next.**

****Relay preserves what the user meant across approvals, provider failures, waiting and future resume  without silently spending, weakening constraints or forgetting the original request.****

> ****Alexa+ understands what the user needs. Relay preserves what they meant and makes sure the task survives the real world.****


<p align="center">
  <a href="https://github.com/agcodes0315/Relaython"><img src="https://img.shields.io/badge/GitHub-Relaython-181717?style=for-the-badge&logo=github&logoColor=white" alt="Relaython GitHub"></a>
  <a href="https://re-a46ae59b318a40bb8cac74dd263154d8.ecs.us-west-2.on.aws"><img src="https://img.shields.io/badge/Live-Deployment-2EA44F?style=for-the-badge&logo=amazonaws&logoColor=white" alt="Live Deployment"></a>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/MCP-2025--11--25-6C47FF?style=for-the-badge" alt="MCP 2025-11-25">
  <img src="https://img.shields.io/badge/AWS-ECS%20%7C%20DynamoDB%20%7C%20EventBridge%20%7C%20Lambda-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white" alt="AWS">
  <img src="https://img.shields.io/badge/License-MIT-222222?style=for-the-badge" alt="MIT License">
</p>

---

## 🌐 Live Deployment

Relay is deployed publicly on Amazon ECS Express (us-west-2), so you can try it without installing anything.

| | |
|---|---|
| **Live deployment** | [https://re-a46ae59b318a40bb8cac74dd263154d8.ecs.us-west-2.on.aws](https://re-a46ae59b318a40bb8cac74dd263154d8.ecs.us-west-2.on.aws) |
| **Hosted on** | Amazon ECS Express · us-west-2 |


> Provider details, prices, availability, bookings and payment are simulated in the hackathon demo. Do not use the live deployment to authorize real payments.

---

## 🚀 Quick Start

Relay has two demo flows: **HomeOps**, which demonstrates durable service delegation, and **Relay Shield**, which demonstrates scam-payment protection with trusted-family approval. The backend is a Python MCP server; the browser demo lives in `relay-ui/`.

### Requirements
- Python 3.12+
- Node.js and npm (for the web UI)
- AWS credentials and configured `RelayTasks` / `RelayAudit` DynamoDB tables for persistent task and case workflows
- A `RELAY_SHIELD_SECRET` for Relay Shield approval codes

### 1. Start the backend

From the repository root:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
export RELAY_SHIELD_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python server.py
```

On Windows PowerShell, set the secret with:
```powershell
$env:RELAY_SHIELD_SECRET = python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Check the server at [http://localhost:8000/health](http://localhost:8000/health). The health endpoint works without AWS; persistence, scheduling, and case workflows require valid AWS configuration and the tables listed above.

### 2. Start the web demo

Open a second terminal:

```bash
cd relay-ui
npm install
node server/bridge.mjs
```

Open a third terminal, then run:

```bash
cd relay-ui
npm run dev
```

Open the local URL printed by Vite and choose the HomeOps or Relay Shield experience. The bridge is configured to use the deployed MCP endpoint by default. For local-backend testing, update `MCP_URL` in `relay-ui/server/bridge.mjs` to `http://127.0.0.1:8000/mcp`, then restart the bridge.

### 3. Run tests

From the repository root, with the virtual environment active:

```bash
python -m pytest
```

This runs the offline unit-test suite. Integration tests need AWS credentials and configured resources; public end-to-end tests call the deployed endpoint. See [Testing](#-testing) and [`docs/relay-shield-testing.md`](./docs/relay-shield-testing.md).

**Important:** Provider details, prices, availability, bookings and payment are simulated in the hackathon demo. Do not use the demo to authorize real payments. Never commit `.env` files, AWS credentials, or the Shield secret.

---

## 🎯 The Problem

AI assistants are good at understanding what a user wants.

The harder problem begins ****after the conversation****.

A real-world request may involve money, external providers, waiting, failures and decisions that happen minutes, hours or days later.

For example:

> ****"Alexa, get my AC serviced this week under ₹2,000, but not Thursday."****

Understanding that sentence is easy.

What happens when:

- the selected provider fails after approval?

- another provider costs more than the user's budget?

- the task has to wait until later?

- the application restarts?

- the original conversation is gone?

- the system needs to explain what changed and why?

****Relay is designed for that part of the problem.****

Most assistants are optimized for:

```text

ask → answer

```

Relay is designed for:

```text

understand

   ↓

persist intent

   ↓

act

   ↓

ask the human when required

   ↓

wait

   ↓

recover from failure

   ↓

resume later

   ↓

explain what happened

```

---

## ⚡ Problem → Task → Actions → Results

| | |
|---|---|
| **Problem** | Real-world agent tasks outlive the conversation: providers fail, approvals become stale, constraints can be lost, and work may need to resume later. |
| **Task** | Build a durable execution layer for Alexa+-style agents that preserves user intent and authority across failure, waiting and recovery. |
| **Actions** | Implemented a self-hosted MCP server with deterministic policy, context-bound approvals, constraint revalidation, DynamoDB persistence, EventBridge scheduling, Lambda resume and decision receipts. |
| **Results** | **17 tools · 2 resources · 1 prompt**, HomeOps **7/7**, preflight **6/6**, safety **6/6**, public recovery/resume validations passed, representative remote tool-call **p95 381.9 ms**, and **100/100** successful synthetic load requests. |

> **Outcome:** Relay preserves the original task contract, invalidates stale approval after execution context changes, recovers only within the user's constraints, and resumes persisted work later.

---

## 🧭 What Happens After the Conversation Ends?

```mermaid
flowchart TD
    A[Alexa+-style assistant understands intent] --> B[Relay captures a durable task contract]
    B --> C[Task leaves the conversation]
    C --> D{Real-world execution}
    D --> E[Provider changes]
    D --> F[Human approval]
    D --> G[Waiting]
    D --> H[Failure]
    E --> I[DynamoDB preserves state]
    F --> I
    G --> I
    H --> I
    I --> J[EventBridge schedules a future wake-up]
    J --> K[Lambda restores persisted state]
    K --> L[Relay revalidates constraints]
    L --> M[Task continues safely]
```

**Relay is not an AC-service bot. HomeOps is the demonstration domain for a reusable durable-agent execution primitive.**

The same execution pattern can support travel disruption recovery, repair coordination, procurement, event vendors, recurring errands, appointment workflows, document follow-up, relocation and subscription management.

> The core idea is simple: **preserve intent, preserve authority, survive change, and resume safely.**

---

## 🧠 The Relay Contract

Relay turns conversational intent into a ****durable execution contract****.

```text

Goal

\+ Budget

\+ Deadline

\+ Excluded days

\+ Human authority

\+ Approval state

\+ Provider state

\+ Recovery state

\+ Resume state

```

That contract becomes the source of truth for the task.

The agent may adapt to changing circumstances, but it cannot silently rewrite what the user asked.

### Why this matters

A conversational agent may know what the user said **right now**. A real-world execution system must also remember:

- what may be changed,

- what must never be changed,

- what requires approval,

- whether an approval is still valid,

- what has already failed,

- what should happen after waiting,

- how to continue later.

Relay externalizes that state instead of relying only on conversational memory.

---

## 🏆 The Core Demonstration

This is the most important Relay story: a user asks for AC servicing under a budget, a provider fails after approval, and Relay recovers using the **original** rules, then resumes later.

> ****Relay refuses to forget the user's rules when the world changes.****

That is the central design principle of the project.

<details>
<summary><b>📖 Click to expand: the full step-by-step flow of this story</b></summary>

<br>

```text

User:

"Get my AC serviced this week

under ₹2,000,

but not Thursday."

        ↓

Relay stores the contract

        ↓

QuickFix ₹1,800

        ↓

Human approval required

        ↓

User approves

        ↓

QuickFix becomes unavailable

        ↓

Old approval becomes invalid

        ↓

Relay reapplies the ORIGINAL contract

        ↓

PremiumAir ₹2,600 → rejected

Thursday options → rejected

Late options → rejected

        ↓

CoolCare ₹1,450 remains valid

        ↓

Fresh human approval required

        ↓

Task waits

        ↓

EventBridge wakes the task later

        ↓

Lambda restores persisted state

        ↓

TASK_RESUMED

        ↓

Decision Receipt explains everything

```

</details>

---

## 🧩 Responsibility

Relay converts conversational intent into ****durable, policy-governed execution state****.

Its responsibilities are to:

- preserve user constraints outside conversational memory,

- expose actions through MCP,

- separate reversible from irreversible actions,

- require human approval before spend-related commitments,

- recover safely when providers fail,

- reapply the original contract during recovery,

- invalidate stale approvals when execution context changes,

- resume persisted work later,

- maintain an auditable decision trail,

- clearly distinguish real infrastructure from simulated hackathon integrations.

---

## ⚙️ Implementation

Relay is implemented as a self-hosted MCP backend using ****Streamable HTTP**** and MCP protocol ****2025-11-25****.

The implementation combines:

- ****17 MCP tools****

- ****2 MCP resources****

- ****1 MCP prompt****

- deterministic safety and state validation

- DynamoDB task and audit state

- EventBridge Scheduler

- AWS Lambda resume worker

- public Amazon ECS Express deployment

- Amazon ECR container images

- optional Amazon Bedrock orchestration

- React + Node simulated Alexa+ experience

<details>
<summary><b>🔄 Click to expand: the end-to-end execution lifecycle</b></summary>

<br>

```text

understand

   ↓

clarify

   ↓

persist contract

   ↓

search / propose

   ↓

evaluate risk

   ↓

ask human when required

   ↓

recover if a provider fails

   ↓

schedule a future wake-up

   ↓

restore persisted state

   ↓

resume

   ↓

explain through an audit trail

```

</details>

---

## 📈 Verified Results

| Result | Verified Outcome |
|---|---:|
| MCP tools | ****17**** |
| MCP resources | ****2**** |
| MCP prompts | ****1**** |
| MCP protocol | ****2025-11-25**** |
| HomeOps tests | ****7/7 passed**** |
| Preflight tests | ****6/6 passed**** |
| Safety tests | ****6/6 passed**** |
| Public failure-recovery test | ****Passed**** |
| Public durable-resume test | ****Passed**** |
| Representative remote tool-call p95 | ****381.9 ms**** |
| Synthetic concurrent-load test | ****100/100 successful requests**** |
| Synthetic concurrency | ****25 clients**** |
| Durable-state tables | ****2**** |
| Human approval before spend | ****Required**** |
| License | ****MIT**** |

> The concurrency test is a synthetic resilience test, not a claim of production-scale live-user traffic. Under that load, p95 latency increased to approximately ****2.69 seconds****.

---

# 🛡️ Relay Shield — Scam-Payment Protection

Relay Shield extends Relay's durable execution model to a high-stakes situation: a suspicious message arrives and a payment may be about to move. It scores scam signals, applies a deterministic payment policy, and can place a payment on hold while a trusted family member reviews the case.

> **If nobody responds, the payment remains blocked. A model can recommend; it cannot authorize a payment.**

### How it works

1. **Analyze the message:** `analyze_message` returns a risk score and signals. An optional model can provide a second opinion, but it can only increase the score; rule-based scoring still works without it.
2. **Assess the payment:** `assess_scam_risk` considers the risk score, payment amount and whether the payee is new, then returns `ALLOW`, `WARN`, `HOLD` or `BLOCK`.
3. **Open a protection case:** A hold is persisted in DynamoDB, an alert is sent to the first trusted contact, and escalation/expiry timers are scheduled.
4. **Request trusted-family approval:** The family inbox provides a one-time approval code. A valid decision can approve or reject the case; the assistant does not receive the approval code.
5. **Escalate or fail closed:** EventBridge Scheduler can trigger the Lambda resume worker to contact the next trusted person or expire the hold. If nobody responds, the payment stays blocked.
6. **Review the receipt:** An audit trail records the case's decisions and state transitions.

### What was added

Relay Shield adds **9 MCP tools, 1 resource and 1 prompt** to the original Relay surface, bringing the combined server to **26 tools, 3 resources and 2 prompts**. It reuses the existing DynamoDB tables, EventBridge Scheduler, Lambda worker and deterministic policy approach; the original 17 Relay tools remain unchanged.

<details>
<summary><b>🧱 Click to expand: what each Shield component protects</b></summary>

<br>

| Area | What it protects |
|---|---|
| Scam scoring and classifier | Identifies suspicious-message signals; optional model output cannot lower the rule-based score |
| Payment policy | Chooses allow, warn, hold or block based on risk and payment context |
| Case state machine | Restricts transitions to valid states and prevents late events from overwriting newer decisions |
| Family approval codes | Uses one-time, context-bound codes and rejects invalid, expired or replayed decisions |
| Timers and escalation | Escalates to trusted contacts and blocks the payment when the hold expires |
| Shield UI and tests | Demonstrates the protection flow and checks scoring, policy, state, security and Lambda behavior |

</details>

**Hackathon boundary:** Relay Shield demonstrates a payment-protection workflow; it does not connect to a real bank or execute, release, or reverse real payments. The family inbox and payment context are part of the demo. Configure `RELAY_SHIELD_SECRET` before running Shield, and keep it private.

Further details: [Shield design](./docs/relay-shield-design.md) · [Operations guide](./docs/relay-shield-operations.md) · [API reference](./docs/relay-shield-api.md) · [Security notes](./docs/relay-shield-security.md) · [Testing guide](./docs/relay-shield-testing.md).

---

# 🏠 Relay HomeOps

### Context-Aware Home Asset, Warranty and Service Orchestration

Relay HomeOps lets the workflow begin from the actual user problem, such as "Alexa, my AC isn't cooling properly", and carries it through asset lookup, warranty context, troubleshooting, delegation, approval, recovery and resume.

<details>
<summary><b>🔄 Click to expand: the HomeOps flow, from problem to decision receipt</b></summary>

<br>

```text

"Alexa, my AC isn't cooling properly."

        ↓

known household asset

        ↓

stored warranty context

        ↓

safe first-line troubleshooting

        ↓

service required?

        ↓

durable delegation contract

        ↓

provider search

        ↓

human approval

        ↓

failure recovery

        ↓

durable wait / resume

        ↓

decision receipt

```

</details>

### 🎥 Demo Coverage

The **HomeOps capabilities are implemented in the public MCP backend**. The simulated Alexa+ client focuses on the durable delegation lifecycle: contract creation, provider selection, approval, failure recovery, waiting, resume and audit.

For the hackathon demo, household assets, order history, warranty data, providers, pricing, availability, booking and payment are simulated. This was intentional: the implementation effort focused on the harder systems problem of preserving user intent, enforcing safety boundaries, recovering from failure and resuming durable work later.

The repository includes public backend validation for HomeOps asset lookup, warranty checking, conservative troubleshooting and service preparation.

### HomeOps Backend Proof

The current simulated Alexa+ frontend demonstrates the service-delegation, approval, recovery and resume flow.

HomeOps asset, warranty and troubleshooting capability is validated directly against the ****public MCP backend****.

<p align="center">

  <img src="docs/images/01-homeops-backend-proof.jpeg" alt="Relay HomeOps public MCP backend proof" width="95%">

</p>

### Demo Asset

The demo uses one simulated household asset: a CoolBreeze Split AC (model CB-24X) in the bedroom.

<details>
<summary><b>📋 Click to expand: full demo asset details</b></summary>

<br>

| Field | Value |
|---|---|
| Product | CoolBreeze Split AC |
| Model | CB-24X |
| Purchased | 2026-03-12 |
| Warranty expiry | 2027-03-12 |
| Retailer | Amazon |
| Location | Bedroom |

</details>

The household asset, order, warranty, provider, pricing and payment data shown in the demo are **simulated demo data**.

---

# 🖥️ Simulated Alexa+ Experience

The React frontend is a simulated Alexa+-style interface connected to the real Relay MCP backend.

It demonstrates:

- delegation,

- provider options,

- risk and approval state,

- failure recovery,

- durable wait,

- resume status,

- decision receipts.

The client surface is intentionally labeled **Simulated Alexa+ Experience**.

---

# 📝 Durable Delegation Contract

Relay persists the user's intent as a contract rather than relying only on conversational memory.

<p align="center">

  <img src="docs/images/02-delegation-contract.jpeg" alt="Relay delegation contract and provider options" width="95%">

</p>

Example contract:

| Constraint | Value |
|---|---|
| Goal | AC servicing |
| Maximum budget | ₹2,000 |
| Deadline | 10 Oct 2026 |
| Excluded day | Thursday |
| Spend authority | Human only |

Relay persists:

- goal

- budget

- deadline

- excluded weekdays

- selected provider

- approval state

- recovery state

- wait status

- resume count

- audit history

---

# 🛡️ Deterministic Safety Policy

Important constraints are enforced by Relay itself rather than delegated solely to a model.

| Check | Behavior |
|---|---|
| Budget | reject providers above the user's maximum |
| Deadline | reject providers that miss the deadline |
| Excluded weekdays | reject explicitly prohibited days |
| State transitions | prevent invalid workflow jumps |
| Provider validity | select only available providers |
| Spend | require explicit human approval |
| Recovery | reapply the original contract after failure |

Risk model:

```text

SEARCH        → LOW

PROPOSE       → LOW

SELECT        → MEDIUM / reversible

BOOK          → HIGH / approval required

unknown       → fail-safe / approval required

```

---

# 👤 Human Approval Gate

Relay separates recommendation from authorization.

<p align="center">

  <img src="docs/images/03-human-approval.jpeg" alt="Relay human approval required before spend" width="95%">

</p>

```text

Provider selected

      ↓

BOOK_PROVIDER evaluated

      ↓

REQUIRE_APPROVAL

      ↓

Human approves

      ↓

USER_APPROVED

```

Relay can search and recommend autonomously, but it cannot authorize spending on the user's behalf.

---

## 🔐 Context-Bound Approval

Approval in Relay belongs to a **specific execution context**.

If that context changes materially for example, if the selected provider fails the previous approval is invalidated.

```text

QuickFix ₹1,800 approved

        ↓

QuickFix fails

        ↓

execution context changed

        ↓

previous approval invalidated

        ↓

replacement option evaluated

        ↓

fresh approval required

```

Relay therefore does **not** treat consent as a reusable permission token.

Human approval remains tied to the action the user actually reviewed.

---

## ♻️ Constraint Revalidation

Recovery must never weaken the original task contract.

When a provider fails, Relay re-evaluates replacement options against the original:

- budget,

- deadline,

- excluded weekdays,

- provider availability,

- approval boundary.

Only compliant alternatives can move forward.

This behavior was strengthened after testing exposed a recovery case in which an invalid replacement could reappear. The bug was fixed and regression-tested.

---

# 🔁 Failure Recovery

The strongest part of the demo is what happens when the real world changes after approval.

<p align="center">

  <img src="docs/images/04-failure-recovery.jpeg" alt="Relay provider failure recovery with approval invalidation and constraint revalidation" width="95%">

</p>

<details>
<summary><b>🔄 Click to expand: the recovery sequence, state by state</b></summary>

<br>

```text

QuickFix selected ₹1,800

      ↓

human approval

      ↓

QuickFix becomes unavailable

      ↓

PROVIDER_FAILED

      ↓

old approval invalidated

      ↓

RECOVERY_STARTED

      ↓

original constraints reapplied

      ↓

invalid providers rejected

      ↓

CoolCare proposed ₹1,450

      ↓

fresh human approval required

```

</details>

An earlier recovery defect allowed an option outside the original contract to reappear. The issue was reproduced, fixed and regression-tested.

See the [Hackathon Friction Log](./docs/friction-log.md).

---

# ⏰ Durable Wait and Resume

Relay does not depend on an open browser tab or an in-memory timer.

<p align="center">

  <img src="docs/images/05-durable-resume.jpeg" alt="Relay durable EventBridge and Lambda task resume" width="95%">

</p>

<details>
<summary><b>🔄 Click to expand: the persisted wait/resume workflow and public validation</b></summary>

<br>

The persisted workflow is:

```text

Task

  ↓

DynamoDB

  ↓

WAIT_SCHEDULED

  ↓

EventBridge Scheduler

  ↓

future trigger

  ↓

Lambda

  ↓

RESUME_TRIGGERED

  ↓

STATE_RESTORED

  ↓

TASK_RESUMED

```

Public validation confirmed:

```text

WAIT_SCHEDULED   ✓

RESUME_TRIGGERED ✓

STATE_RESTORED   ✓

TASK_RESUMED     ✓

Resume count: 1

```

</details>

---

# 🧾 Decision Receipt

Every important execution transition produces an auditable event.

The receipt lets a user or developer answer:

- What did Relay understand?

- Which constraints were enforced?

- Why was an option rejected?

- Who approved spending?

- What failed?

- Why did Relay choose a replacement?

- When was the task resumed?

- What state was restored?

<details>
<summary><b>📋 Click to expand: all representative audit events and what they mean</b></summary>

<br>

| Event | Meaning |
|---|---|
| `TASK_CREATED` | delegation stored |
| `POLICY_EVALUATED` | deterministic policy checked |
| `PROVIDERS_FILTERED` | invalid providers removed |
| `OPTIONS_PROPOSED` | valid choices returned |
| `PROVIDER_SELECTED` | provider selected |
| `USER_APPROVED` | human approval recorded |
| `PROVIDER_FAILED` | provider failed |
| `RECOVERY_STARTED` | recovery began |
| `WAIT_SCHEDULED` | future resume scheduled |
| `RESUME_TRIGGERED` | Lambda wake-up |
| `STATE_RESTORED` | persisted task reloaded |
| `TASK_RESUMED` | task continued |

</details>

The goal is to make agent behavior inspectable rather than opaque.

---

# 🏗️ Architecture

```mermaid

flowchart TD

    U[User] --> A[Simulated Alexa+ Experience]

    A --> B[Node MCP Bridge]

    B --> C[Relay MCP Server<br/>Streamable HTTP<br/>Amazon ECS Express]

    C --> H[HomeOps Context]

    C --> P[Deterministic Policy]

    C --> T[MCP Tools]

    C --> R[Recovery Logic]

    C --> S[Scheduler Logic]

    H --> D[(Amazon DynamoDB)]

    T --> D

    R --> D

    S --> E[Amazon EventBridge Scheduler]

    E --> L[AWS Lambda<br/>RelayResumeWorker]

    L --> D

    C --> AU[(RelayAudit)]

    AU --> D

    AG[Optional Bedrock Agent Layer] --> T

    AG --> BR[Amazon Bedrock]

```

<details>
<summary><b>🔄 Click to expand: durable resume path and responsibility boundary</b></summary>

<br>

### Durable Resume Path

```text

Relay task

   ↓

DynamoDB

   ↓

WAIT_SCHEDULED

   ↓

EventBridge Scheduler

   ↓

Lambda

   ↓

RESUME_TRIGGERED

   ↓

STATE_RESTORED

   ↓

TASK_RESUMED

```

### Responsibility Boundary

```text

Alexa+-style client

        ↓

conversation / intent

        ↓

Relay

        ↓

durable external task state

constraints

risk policy

approval state

recovery state

resume state

audit history

```

</details>

Relay does **not** claim to replace Alexa+ conversational continuity. It focuses on durable execution outside the conversation.

---

# 🔌 MCP Surface

Relay exposes **17 tools, 2 resources and 1 prompt** over MCP.

<details>
<summary><b>🧰 Click to expand: all 17 tools and what each one does</b></summary>

<br>

## 17 Tools

| Tool | Responsibility |
|---|---|
| `clarify_delegation` | detect missing constraints |
| `assess_action_risk` | classify risk and approval requirements |
| `create_errand` | create a durable task contract |
| `get_errand` | load persisted task state |
| `find_providers` | filter providers against constraints |
| `propose_options` | present valid provider options |
| `select_provider` | select a reversible option |
| `approve_booking` | record explicit human approval |
| `get_audit_log` | retrieve the decision receipt |
| `simulate_provider_failure_tool` | simulate provider cancellation |
| `restore_provider` | restore provider state after testing |
| `schedule_task_resume` | schedule a future wake-up |
| `list_household_assets` | list demo HomeOps assets |
| `get_household_asset` | retrieve one asset |
| `check_warranty` | evaluate stored warranty state |
| `troubleshoot_home_asset` | return conservative troubleshooting |
| `prepare_service_from_asset` | convert asset context into a Relay service contract |

</details>

## 2 Resources

```text

relay://home/assets

relay://home/assets/{asset_id}

```

## 1 Prompt

```text

resolve_home_issue

```

---

# ⚡ Performance Validation

Remote MCP calls have a median of roughly 270 ms and a worst-case p95 of 381.9 ms. A synthetic load test of 100 requests across 25 clients all succeeded.

<details>
<summary><b>📊 Click to expand: full latency tables and load-test numbers</b></summary>

<br>

### Representative Remote MCP Calls

50 measured runs after warm-up:

| Operation | Median | p95 |
|---|---:|---:|
| `/health` | 269.1 ms | 362.7 ms |
| `tools/list` | 271.5 ms | 358.7 ms |
| `assess_action_risk` | 272.8 ms | 352.0 ms |
| `get_errand` | 275.8 ms | **381.9 ms** |

### Synthetic Concurrent Load

```text

Concurrency: 25

Requests:    100

Successful:  100/100

Throughput:  ~10.08 successful requests/sec

Median:      ~2313.5 ms

p95:         ~2693.8 ms

```

</details>

This is a resilience test, not a claim of production-scale live-user performance.

---

# ☁️ AWS Builder Integration

Relay's AWS story is not a single model call. The durable execution lifecycle crosses multiple AWS services.

| AWS Service | Use |
|---|---|
| Amazon ECS Express | hosts the public MCP server |
| Amazon ECR | stores container images |
| Amazon DynamoDB | stores task and audit state |
| Amazon EventBridge Scheduler | schedules durable future wake-ups |
| AWS Lambda | restores and resumes tasks |
| Amazon Bedrock | optional model orchestration |
| AWS IAM | execution, task and scheduler permissions |

Critical continuation path:

```text

MCP Server

   ↓

DynamoDB

   ↓

EventBridge Scheduler

   ↓

Lambda

   ↓

DynamoDB

   ↓

resumed task

```

This is the AWS path that allows Relay to continue even after the original request/interaction is over.

### 📸 AWS Deployment Evidence

Real AWS screenshots of the ECS deployment, the EventBridge resume schedule and the Lambda invocation metrics are included below.

<details>
<summary><b>📸 Click to expand: evidence table and AWS console screenshots</b></summary>

<br>

| Evidence | Proof |
|---|---|
| Amazon ECS Express | public `relay-mcp` service active and running |
| Amazon ECR | deployed `homeops-v2` container image |
| Amazon DynamoDB | `RelayTasks` durable contracts and `RelayAudit` decision events |
| Amazon EventBridge Scheduler | live `relay-resume-*` future wake-up |
| AWS Lambda | `RelayResumeWorker` restores/resumes persisted tasks |
| CloudWatch/Lambda metrics | successful invocations with zero errors in captured run |
| Amazon Bedrock | optional `openai.gpt-oss-20b` model configuration/catalog evidence |

<p align="center">
  <img src="docs/images/aws/01-ecs-relay-mcp.jpeg" alt="Relay MCP service on Amazon ECS Express" width="92%">
</p>

<p align="center"><em>Real AWS deployment: Relay's public MCP server running on Amazon ECS Express.</em></p>

<p align="center">
  <img src="docs/images/aws/05-eventbridge-relay-resume.jpeg" alt="Relay durable EventBridge resume schedule" width="92%">
</p>

<p align="center"><em>Real durable continuation: EventBridge Scheduler targets RelayResumeWorker for a future wake-up.</em></p>

<p align="center">
  <img src="docs/images/aws/07-lambda-resume-invocation.jpeg" alt="RelayResumeWorker Lambda invocation metrics" width="92%">
</p>

<p align="center"><em>Real resume execution: RelayResumeWorker invocation evidence from AWS Lambda.</em></p>

> Additional AWS screenshots are kept under `docs/images/aws/`.

</details>

---

# 🌐 Public MCP Endpoint

### MCP

```text

https://re-4f589c522a0645c5b9f2ead60f3e7516.ecs.us-west-2.on.aws/mcp

```

### Health

```text

https://re-4f589c522a0645c5b9f2ead60f3e7516.ecs.us-west-2.on.aws/health

```

Protocol:

```text

2025-11-25

```

---

# 🤖 Optional Amazon Bedrock Agent Layer

Relay includes a separate optional model-orchestration layer using Amazon Bedrock.

Default model configuration:

```text

openai.gpt-oss-20b

```

The polished UI calls Relay MCP tools directly.

Deterministic safety, provider filtering, approval boundaries, recovery and task state do **not** depend on the model.

This separation is intentional: generative reasoning can help orchestration, while policy-critical decisions remain deterministic and inspectable.

---

# 🧪 Testing

Unit tests run offline with a single command. Integration tests need AWS credentials, and the public end-to-end tests call the deployed endpoint.

### Unit tests (offline)

Run from the repository root. `pytest.ini` makes the default command run only the offline unit tests in `tests/unit/`:

```bash
python -m pytest
```

<details>
<summary><b>🧪 Click to expand: individual test modules and validated results</b></summary>

<br>

To run an individual unit test module:

```bash
python -m pytest tests/unit/test_homeops.py -v
python -m pytest tests/unit/test_improvement_guards.py -v
python -m pytest tests/unit/test_preflight.py -v
python -m pytest tests/unit/test_relay_safety.py -v
```

Validated:

```text

HomeOps:   7/7 passed

Preflight: 6/6 passed

Safety:    6/6 passed

```

</details>

<details>
<summary><b>☁️ Click to expand: integration and public AWS test commands</b></summary>

<br>

### Integration (needs AWS credentials)

Run from the repository root:

```bash
python -m tests.integration.test_dynamodb
python -m tests.integration.test_recovery
python -m tests.integration.test_scheduler
```

### Public AWS

```powershell

python tests/e2e/test_mcp_http.py

python tests/e2e/test_homeops_public.py

python tests/e2e/test_recovery_public.py

python tests/e2e/test_resume_public.py

```

Validated:

```text

Public HomeOps MCP validation: passed

Public failure recovery:       passed

Public durable resume:         passed

```

</details>

---

# 🌍 One Demo Domain, General Execution Primitive

HomeOps is Relay's demonstration domain.

The underlying execution model is reusable anywhere a task must survive changing external conditions.

Potential applications include:

- travel disruption recovery,

- household maintenance,

- procurement,

- appointment coordination,

- event vendors,

- relocation,

- recurring errands,

- subscription changes,

- document follow-ups,

- multi-step purchasing workflows.

The common problem is the same:

> **preserve intent, preserve authority, survive change, and resume safely.**

Relay is therefore **not an AC-service bot**. HomeOps is the proof domain for a reusable durable-agent execution primitive.

---

# 💡 Why Relay Is More Than a Basic MCP Wrapper

Relay is not simply an API placed behind MCP.

It adds execution semantics around the tools:

- durable contracts,

- deterministic policy,

- risk classification,

- human approval,

- approval invalidation,

- failure recovery,

- constraint revalidation,

- scheduled waiting,

- persistent state restoration,

- decision receipts.

The value comes from how those components work together across time and failure.

---

# 🎯 Judging Alignment

### Technical Implementation

Relay demonstrates a working self-hosted MCP server, public AWS deployment, persistent state, event-driven resumption, deterministic safety controls, automated tests and remote validation.

### Design

The system separates:

- conversation from execution state,

- model reasoning from hard policy,

- reversible actions from irreversible commitments,

- old consent from changed execution context.

### Potential Impact

The same durable execution pattern can extend beyond HomeOps into commerce, travel, events, procurement, relocation and other long-running agentic workflows.

### Quality of the Idea

Relay focuses on a problem that becomes more important as assistants become more agentic:

> **What happens after the assistant understands the request?**

Its answer is durable execution with explicit user authority.

---

# 🧭 Amazon Leadership Principles Reflected in the Engineering

Relay is not an Amazon product and this section does not imply Amazon endorsement. It explains how the engineering decisions reflect similar problem-solving behaviors.

<details>
<summary><b>🧭 Click to expand: all 16 principles and how Relay reflects each</b></summary>

<br>

| Leadership Principle | How Relay Reflects It |
|---|---|
| **Customer Obsession** | user constraints, safety boundaries and approval authority remain the source of truth |
| **Ownership** | the workflow owns recovery, resume and audit instead of handing failure back to the user |
| **Invent and Simplify** | durable execution is reduced to an explicit task contract and MCP surface |
| **Are Right, A Lot** | deterministic policy and tests verify assumptions instead of trusting model output blindly |
| **Learn and Be Curious** | the project explores MCP Resources, Prompts, Streamable HTTP, ECS Express, EventBridge, Lambda and Bedrock |
| **Hire and Develop the Best** | documentation, tests and reusable patterns are designed to help future contributors build on the work |
| **Insist on the Highest Standards** | recovery bugs were reproduced and fixed, safety rules regression-tested, and limitations documented |
| **Think Big** | Relay is designed as a reusable durable-execution pattern rather than only an AC-service demo |
| **Bias for Action** | reversible actions proceed quickly while irreversible spending pauses for approval |
| **Frugality** | focused managed AWS services and simulated integrations were used where production APIs were unavailable |
| **Earn Trust** | Relay records decision receipts and clearly discloses simulated integrations |
| **Dive Deep** | debugging covered policy, Docker images, ECS revisions, IAM, MCP transport, DynamoDB and EventBridge/Lambda |
| **Have Backbone; Disagree and Commit** | model autonomy is intentionally constrained where deterministic policy or human approval is safer |
| **Deliver Results** | the system is publicly deployed, tested, benchmarked and versioned |
| **Strive to be Earth's Best Employer** | the human-in-the-loop design keeps people informed and in control of meaningful commitments |
| **Success and Scale Bring Broad Responsibility** | authentication, privacy, provider verification, abuse controls and payment safety are explicitly documented as production requirements |

</details>

---

# ✅ Real vs Simulated

| Simulated for the Hackathon | Real Implementation |
|---|---|
| Alexa+ client surface | MCP Streamable HTTP backend |
| household order records | public AWS-hosted MCP endpoint |
| manufacturer warranty feed | DynamoDB persistence |
| service providers | deterministic policy |
| provider prices / availability | approval boundary |
| actual booking | failure recovery |
| payment / Amazon Wallet | EventBridge scheduled resume |
| provider transaction APIs | Lambda task restoration |
| | audit trail |

---

# 🔐 Security and Production Boundaries

Current controls:

- Host and Origin validation

- deterministic constraint validation

- state-transition validation

- human approval before spend

- provider revalidation after failure

- safe troubleshooting escalation

- audit history

Relay is a hackathon system, so several production controls are still required before real use.

<details>
<summary><b>🔒 Click to expand: production hardening still required</b></summary>

<br>

Production hardening still required:

- production authentication

- per-user authorization

- per-task authorization

- secret management

- provider identity verification

- rate limiting

- payment security

- idempotent transactions

- monitoring and abuse controls

- privacy and retention controls

</details>

See [Production Authentication Architecture](./docs/production-auth-architecture.md).

---

## 🧩 Known Hackathon Boundaries

Relay deliberately prioritizes durable execution over breadth of external integrations.

- The polished frontend demonstrates the delegation lifecycle; the full HomeOps asset/warranty flow is validated through the public MCP backend.
- External providers, prices, availability, booking and payment are simulated.
- Production OAuth/account linking and per-user authorization are not implemented; the repository documents the production authentication architecture separately.
- The synthetic load test demonstrates resilience under controlled concurrency, not production-scale live traffic.

These are explicit scope boundaries rather than hidden claims.

---

# ⚠️ Current Scope

Relay does **not** claim:

- production Alexa+ integration

- live Amazon customer order access

- live manufacturer warranty APIs

- real technician booking

- real payment execution

- production authentication

- production provider verification

- production-scale live-user traffic

These boundaries are documented intentionally.

---

# 🛠️ Feature Requests

These requests come directly from the implementation experience while building Relay: better MCP Inspector support, durable workflow primitives for MCP, a local Alexa+ simulator, and an AWS reference architecture for durable MCP agents.

<details>
<summary><b>🛠️ Click to expand: all 4 requests with priority and reasoning</b></summary>

<br>

### 1. MCP Inspector support for end-to-end Streamable HTTP workflows
**Priority:** Important

A workflow-oriented inspector that can preserve task context across multiple MCP tool calls would make durable-agent debugging significantly easier.

### 2. First-class durable workflow primitives for MCP
**Priority:** Nice-to-have

Standard patterns for wait, resume, approval invalidation and state restoration would reduce custom infrastructure for long-running MCP agents.

### 3. Easier Alexa+ local simulation for self-hosted MCP servers
**Priority:** Important

A locally available Alexa+-style testing harness would let developers validate conversational and visual integration before gated production access.

### 4. AWS reference architecture for durable MCP agents
**Priority:** Nice-to-have

A documented ECS + DynamoDB + EventBridge Scheduler + Lambda pattern would shorten onboarding for developers building long-running MCP workflows.

</details>

---

# 🌱 What's Next

| Expansion | Example |
|---|---|
| Relay Commerce | contextual procurement and cart optimization |
| Relay Events | multi-vendor event coordination |
| Relay Move | relocation orchestration |
| Relay Kitchen | pantry and grocery workflows |
| Relay Travel | long-running trip coordination |
| Relay Asset Vault | real warranty and receipt integrations |
| DurableMCP | reusable open-source durable MCP starter |

The hackathon flagship remains **HomeOps**.

---

# 🗣️ Judge Pitch

### 10-second version

> **Relay is the execution layer for Alexa+-style agents. It turns a user's request into a durable contract that survives provider failures, human approvals, waiting and future resume without forgetting or weakening what the user originally asked.**

### 20-second version

> **Most assistants are good at understanding a request, but real tasks continue after the conversation ends. Relay externalizes the user's intent into durable state. If a provider fails after approval, Relay invalidates the old approval, reapplies the original constraints, finds a compliant alternative, asks again when required, and can resume later through EventBridge and Lambda.**

---

# 📁 Repository Structure

The repository is split into the MCP backend (`relay/`), the React UI (`relay-ui/`), the Lambda resume worker, infrastructure config, scripts, tests and docs.

```text
Relaython/
├── server.py                     # MCP server entry point
├── relay/                        # Core Relay backend
│   ├── policy.py                 # Deterministic action and safety policy
│   ├── store.py                  # Durable task/state persistence
│   ├── recovery.py               # Provider-failure recovery
│   ├── scheduler.py              # Durable wait and resume scheduling
│   ├── tools.py                  # MCP tool definitions and handlers
│   ├── home_assets.py            # HomeOps assets, warranty and service context
│   └── scam/                     # Relay Shield scam-protection workflow
│       ├── classifier.py         # Scam classification
│       ├── scoring.py             # Risk scoring
│       ├── policy.py              # Payment and safety decisions
│       ├── service.py             # Shield workflow/service logic
│       ├── tokens.py              # Family approval-code handling
│       └── receipt.py             # Shield decision receipts
├── relay-ui/                     # React/Vite UI and Node bridge
│   ├── server/bridge.mjs         # UI-to-backend bridge
│   └── src/                      # HomeOps and Relay Shield experiences
├── lambda/
│   └── resume_worker/handler.py  # Lambda worker for durable task resume
├── infra/
│   ├── iam/                      # AWS IAM trust and runtime policies
│   └── legacy-apprunner/         # Earlier App Runner configuration
├── scripts/
│   ├── benchmarks/               # MCP latency and load tests
│   ├── bedrock/                  # Optional Bedrock checks
│   ├── build_lambda.sh           # Lambda build helper
│   └── run_agent.py              # Optional Bedrock agent layer
├── tests/
│   ├── unit/                     # Offline unit and regression tests
│   ├── integration/              # AWS-backed integration tests
│   └── e2e/                      # Public endpoint and workflow checks
├── docs/                         # Hackathon, architecture, security and Shield docs
├── try_shield_tasks.py           # Relay Shield task/demo helper
├── Dockerfile                    # Backend container image
├── requirements.txt              # Local Python dependencies
├── requirements-docker.txt       # Container runtime dependencies
├── pytest.ini                    # Pytest configuration
├── .env.example                  # Environment-variable template
├── LICENSE
└── README.md
```

---

# ⚙️ Running Locally

Run the backend with a Python virtual environment, then start the bridge and UI. Windows PowerShell and macOS / Linux instructions are both included.

### Backend

<details>
<summary><b>🪟 Click to expand: Windows PowerShell setup</b></summary>

<br>

```powershell

python -m venv .venv

Set-ExecutionPolicy `

  -Scope Process `

  -ExecutionPolicy RemoteSigned

.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

python .\server.py

```

</details>

Local endpoints:

```text

http://localhost:8000/health

http://localhost:8000/mcp

```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python server.py
```

### Configuration

Settings are read from environment variables, and every one has a default for local runs.
See [`.env.example`](./.env.example) for the full list. The code does not load `.env` files by itself, so export the values:

```bash
cp .env.example .env
set -a; source .env; set +a
```

- `/health` works without AWS. The task tools need AWS credentials and the `RelayTasks` and `RelayAudit` DynamoDB tables.
- On a deployed host, set `RELAY_PUBLIC_HOST` to the public hostname (comma-separated for several). Requests to hosts that are not listed are rejected by the server's DNS-rebinding protection.
- The optional Bedrock agent layer needs `OPENAI_API_KEY` and is started with `python -m scripts.run_agent`.

<details>
<summary><b>🐧 Click to expand: frontend bridge and UI on WSL / Ubuntu</b></summary>

<br>

### Frontend bridge WSL / Ubuntu

```bash

cd ~/relay-ui

sudo fuser -k 8787/tcp 2>/dev/null || true

nohup node server/bridge.mjs > bridge.log 2>&1 &

curl http://localhost:8787/api/health

```

### Frontend

```bash

cd ~/relay-ui

npm run dev -- --host 0.0.0.0

```

</details>

---

## 🧪 Engineering Friction Log

Relay includes a real development friction log covering recovery-policy defects, stale container deployment, MCP SDK field mismatches, EventBridge/Lambda/IAM setup, AWS authentication friction and Windows/WSL environment issues.

Each entry records:

`Task attempted → Steps taken → Expected result → Actual result → Severity → Workaround → Actionable suggestion`

See [`docs/friction-log.md`](./docs/friction-log.md).

---

# 📚 Documentation

Submission brief, judge demo script, product feedback, friction log, auth architecture, tests and benchmarks are all linked below.

<details>
<summary><b>📚 Click to expand: full documentation and test links</b></summary>

<br>

| Resource | Link |
|---|---|
| Submission Brief | [`docs/SUBMISSION_BRIEF.md`](./docs/SUBMISSION_BRIEF.md) |
| Judge Demo Script | [`docs/JUDGE_DEMO_SCRIPT.md`](./docs/JUDGE_DEMO_SCRIPT.md) |
| Product Feedback | [`docs/product-feedback.md`](./docs/product-feedback.md) |
| Hackathon Friction Log | [`docs/friction-log.md`](./docs/friction-log.md) |
| Production Authentication Architecture | [`docs/production-auth-architecture.md`](./docs/production-auth-architecture.md) |
| HomeOps Tests | [`tests/unit/test_homeops.py`](./tests/unit/test_homeops.py) |
| HomeOps Public Test | [`tests/e2e/test_homeops_public.py`](./tests/e2e/test_homeops_public.py) |
| Safety Tests | [`tests/unit/test_relay_safety.py`](./tests/unit/test_relay_safety.py) |
| Failure Recovery Test | [`tests/e2e/test_recovery_public.py`](./tests/e2e/test_recovery_public.py) |
| Durable Resume Test | [`tests/e2e/test_resume_public.py`](./tests/e2e/test_resume_public.py) |
| Latency Benchmark | [`scripts/benchmarks/benchmark_mcp_latency_v2.py`](./scripts/benchmarks/benchmark_mcp_latency_v2.py) |
| Load Test | [`scripts/benchmarks/load_test_mcp.py`](./scripts/benchmarks/load_test_mcp.py) |
| MIT License | [`LICENSE`](./LICENSE) |
| Repository | [Relaython](https://github.com/agcodes0315/Relaython) |

</details>

---

# 🏆 What Relay Demonstrates

Relay brings together MCP design, durable execution, context-bound approvals, deterministic safety, failure recovery, event-driven AWS infrastructure and public end-to-end validation.

<details>
<summary><b>🏆 Click to expand: the full list of what Relay demonstrates</b></summary>

<br>

Relay brings together:

- MCP tool design

- MCP Resources and Prompts

- Streamable HTTP

- durable task execution

- durable task contracts

- context-bound approvals

- deterministic safety

- state-machine validation

- human-in-the-loop approval

- constraint revalidation

- failure recovery

- scheduled continuation

- persistent cloud state

- event-driven AWS infrastructure

- decision receipts

- benchmarking

- public end-to-end validation

- explicit real-vs-simulated boundaries

</details>

> **A useful real-world agent should not merely know what the user asked. It should preserve the contract, respect the boundaries, survive failure and continue safely when the world changes.**

---

# 👥 Team

### Agrima Saxena
**Software Engineering · Applied AI · Agentic Systems**

<table>
<tr>

<td width="60">
<a href="https://www.linkedin.com/in/agrima-saxena-142960426/" title="LinkedIn">
<img src="https://img.icons8.com/color/48/linkedin.png"
     width="32"
     height="32"
     alt="LinkedIn">
</a>
</td>

<td width="60">
<a href="mailto:agrimalc@gmail.com" title="Email">
<img src="https://img.icons8.com/color/48/gmail-new.png"
     width="32"
     height="32"
     alt="Email">
</a>
</td>

<td width="60">
<a href="https://github.com/agcodes0315" title="GitHub">
<img src="https://img.icons8.com/ios-glyphs/48/ffffff/github.png"
     width="32"
     height="32"
     alt="GitHub">
</a>
</td>

</tr>
</table>

---

### Ayush Verma
**Relay Shield · Scoring and classifier, payment policy, case state machine, family approval codes, timers and Lambda branch, Shield UI, tests and documentation. Co-built Relay Shield with Agrima.**

<table>
<tr>

<td width="60">
<a href="https://www.linkedin.com/in/ayush-verma-1112a0260/" title="LinkedIn">
<img src="https://img.icons8.com/color/48/linkedin.png"
     width="32"
     height="32"
     alt="LinkedIn">
</a>
</td>

<td width="60">
<a href="mailto:ayushverma19171051@gmail.com" title="Email">
<img src="https://img.icons8.com/color/48/gmail-new.png"
     width="32"
     height="32"
     alt="Email">
</a>
</td>

<td width="60">
<a href="https://github.com/Ayush-23479" title="GitHub">
<img src="https://img.icons8.com/ios-glyphs/48/ffffff/github.png"
     width="32"
     height="32"
     alt="GitHub">
</a>
</td>

</tr>
</table>

---

# 📄 License

Relay is released under the [MIT License](./LICENSE).
