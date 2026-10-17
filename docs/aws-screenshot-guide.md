# Relay — AWS Evidence & Screenshot Guide

Use this guide to capture clean evidence for the AWS Builder mini-challenge and the Devpost submission.

## General screenshot rules

Before every screenshot:
- hide browser bookmarks if they contain private information,
- do not expose access keys, secret keys, session tokens or credentials,
- avoid showing unnecessary account IDs,
- avoid showing environment variables or secrets,
- keep the AWS region visible when useful,
- prefer pages that prove the service is actually configured/running.

Suggested folder:

```text
docs/images/aws/
```

Suggested filenames are included below.

---

# Screenshot A — Amazon ECS Express

## Goal
Prove that the Relay MCP server is actually deployed on AWS.

## What to open
AWS Console → Amazon ECS → locate the Relay service/deployment.

Target:
```text
default / relay-mcp
```

## What should be visible
Prefer a page showing:
- service name: `relay-mcp`
- deployment/service status: healthy/running/steady
- region: `us-west-2`
- current task/deployment
- container/image information if visible

## Avoid
- credentials
- unnecessary account identifiers
- unrelated services

## Save as
```text
docs/images/aws/01-ecs-relay-mcp.jpeg
```

## Caption
> **Amazon ECS Express — Relay's public MCP server running as a containerized AWS service.**

---

# Screenshot B — Amazon ECR

## Goal
Prove the Relay container images are stored in AWS.

## What to open
AWS Console → Amazon ECR → Relay repository.

## What should be visible
- repository name
- image tags
- recent Relay image
- preferably the final Relay Shield image tag if visible

Final verified deployment tag:
```text
shield-task13
```

## Save as
```text
docs/images/aws/02-ecr-relay-image.jpeg
```

## Caption
> **Amazon ECR — versioned Relay MCP container images used by the ECS deployment.**

---

# Screenshot C — DynamoDB RelayTasks

## Goal
Prove that task state is durable.

## What to open
AWS Console → DynamoDB → Tables → `RelayTasks`.

## What should be visible
- table name: `RelayTasks`
- table status
- item count or table overview
- preferably one demo item with non-sensitive task fields if safe

Useful task-state fields to show if present:
- status
- budget
- deadline
- selected provider
- approval state
- resume count

## Do not show
- credentials
- any real user data

The demo data is simulated, so it is safe to show only if it contains no secrets.

## Save as
```text
docs/images/aws/03-dynamodb-relaytasks.jpeg
```

## Caption
> **Amazon DynamoDB — RelayTasks persists the user's execution contract and workflow state outside conversational memory.**

---

# Screenshot D — DynamoDB RelayAudit

## Goal
Prove the Decision Receipt / audit trail.

## What to open
AWS Console → DynamoDB → Tables → `RelayAudit`.

## What should be visible
Prefer records/events such as:
```text
TASK_CREATED
POLICY_EVALUATED
PROVIDER_FAILED
RECOVERY_STARTED
WAIT_SCHEDULED
RESUME_TRIGGERED
STATE_RESTORED
TASK_RESUMED
```

Do not worry if one screenshot cannot show all events. A few representative records are enough.

## Save as
```text
docs/images/aws/04-dynamodb-relayaudit.jpeg
```

## Caption
> **Amazon DynamoDB — RelayAudit records inspectable decision and lifecycle events for each durable task.**

---

# Screenshot E — EventBridge Scheduler

## Goal
Prove Relay creates a real future wake-up.

## What to open
AWS Console → Amazon EventBridge → Scheduler / Schedules.

## What should be visible
- a Relay-created schedule
- schedule status
- target
- execution time or schedule expression
- Lambda as the target if visible

## Save as
```text
docs/images/aws/05-eventbridge-relay-resume.jpeg
```

## Caption
> **Amazon EventBridge Scheduler — a persisted Relay task is scheduled to wake in the future instead of relying on an in-memory timer.**

---

# Screenshot F — AWS Lambda

## Goal
Prove the real resume worker exists.

## What to open
AWS Console → Lambda → function:

```text
RelayResumeWorker
```

## What should be visible
- function name
- runtime
- last modified / configuration
- EventBridge trigger if visible

A second optional screenshot can show logs or monitoring for a successful invocation.

## Save as
```text
docs/images/aws/06-lambda-relay-resume-worker.jpeg
```

## Caption
> **AWS Lambda — RelayResumeWorker restores persisted state when EventBridge wakes a durable task.**

---

# Screenshot G — Lambda execution proof (optional but strong)

## Goal
Show that the resume worker actually ran.

## What to open
Lambda → Monitor / CloudWatch logs.

## What should be visible
A successful invocation around the time of a resume test.

If logs contain sensitive identifiers, crop them out.

## Save as
```text
docs/images/aws/07-lambda-resume-invocation.jpeg
```

## Caption
> **Resume execution proof — EventBridge invoked the Lambda worker that restored and resumed the persisted Relay task.**

---

# Screenshot H — Amazon Bedrock

## Goal
Show that Bedrock is an actual integrated AWS component, while keeping claims accurate.

## Important positioning
Relay uses Bedrock as an **optional model-orchestration layer**.

Do NOT claim:
- the primary UI requires Bedrock,
- Bedrock enforces the deterministic safety policy,
- Bedrock performs the real booking,
- the entire Relay architecture depends on Bedrock.

## What to open
AWS Console → Amazon Bedrock.

Choose whichever page most truthfully proves your usage:
- model access / model catalog showing the model used,
- playground/history if it demonstrates an invocation,
- relevant Bedrock usage/configuration page.

Model configured in Relay:
```text
openai.gpt-oss-20b
```

## What should be visible
Ideally:
- Amazon Bedrock branding/page
- the configured/used model
- region
- evidence of access or invocation

## Save as
```text
docs/images/aws/08-bedrock-optional-agent-layer.jpeg
```

## Caption
> **Amazon Bedrock — optional model orchestration for Relay; safety-critical policy, approval and recovery remain deterministic in Relay's MCP backend.**

---

# Screenshot I — AWS architecture proof collage (recommended for Devpost)

After capturing the individual screenshots, create a simple 4-panel collage using:

1. ECS
2. DynamoDB
3. EventBridge Scheduler
4. Lambda

Title:
```text
Relay Durable Execution on AWS
```

Footer:
```text
ECS MCP Server → DynamoDB → EventBridge Scheduler → Lambda → restored state
```

Bedrock can be a small optional callout rather than the center of this diagram.

Suggested filename:
```text
docs/images/aws/09-relay-aws-proof-collage.jpeg
```

## Devpost caption
> **Relay's real AWS execution path: the MCP server runs on ECS, task/audit state persists in DynamoDB, EventBridge schedules future continuation, and Lambda restores the task later. Amazon Bedrock is included as an optional model-orchestration layer.**

---

# Recommended Devpost AWS evidence

If Devpost allows only a small gallery, prioritize:

1. `04-failure-recovery.jpeg`
2. `05-durable-resume.jpeg`
3. `09-relay-aws-proof-collage.jpeg`
4. architecture diagram / README Mermaid
5. human approval screenshot

Do not fill the gallery with many AWS console screenshots. The collage is stronger for judges; the individual screenshots can remain in the repository as evidence.

---

# README section to add after AWS Builder Integration

```markdown
## AWS Evidence

Relay's durable execution path is implemented across real AWS services.

| Evidence | Service |
|---|---|
| MCP server deployment | Amazon ECS Express |
| Container images | Amazon ECR |
| Durable task state | Amazon DynamoDB / RelayTasks |
| Decision Receipt | Amazon DynamoDB / RelayAudit |
| Future wake-up | Amazon EventBridge Scheduler |
| Resume worker | AWS Lambda / RelayResumeWorker |
| Optional model orchestration | Amazon Bedrock |

Screenshots and proof artifacts are stored under:

`docs/images/aws/`
```
