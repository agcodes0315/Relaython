# Relay — Product Feedback

This document covers the developer tools, APIs, SDKs and AWS services used while building Relay for the Amazon Developer Hackathon 2026.

---

## 1. Model Context Protocol (MCP)

### What I used it for
Relay is implemented as a self-hosted MCP server using Streamable HTTP and MCP protocol version 2025-11-25.

Relay exposes:
- 17 tools
- 2 resources
- 1 prompt

The MCP surface handles task creation, risk assessment, provider filtering, approval, failure recovery, durable resume, HomeOps asset context, warranty checks and troubleshooting.

### What worked well
- The protocol makes tool responsibilities explicit.
- Tools, Resources and Prompts provide a clean separation between actions, contextual data and reusable agent instructions.
- Streamable HTTP fits a remotely hosted agent service well.
- Structured tool inputs made deterministic policy checks easier to validate.
- The protocol is flexible enough to expose both short-lived actions and long-running workflow primitives.

### What needs work
- SDK naming conventions can create friction across generated protocol fields and Python/Pydantic attributes. During testing, fields such as `resourceTemplates` and `uriTemplate` had to be accessed as `resource_templates` and `uri_template`.
- Durable multi-step workflow debugging is still more manual than single-tool debugging.
- A first-class workflow-aware MCP Inspector would help developers inspect state across several tool calls.

### Onboarding experience
The core MCP concepts were understandable quickly, but moving from a basic tool server to a durable multi-step workflow required deeper experimentation with resources, prompts, Streamable HTTP and client behavior.

### Would I build with it again?
**Yes.**

MCP is a strong fit for systems where an agent needs structured access to tools and context while keeping execution logic outside the model.

---

## 2. Amazon ECS Express

### What I used it for
Amazon ECS Express hosts Relay's public MCP server.

Public endpoint:

```text
https://re-4f589c522a0645c5b9f2ead60f3e7516.ecs.us-west-2.on.aws/mcp
```

### What worked well
- Containerized deployment made local and cloud behavior closely aligned.
- The public HTTPS endpoint made remote MCP validation straightforward.
- ECS allowed the Relay server to remain independent from the frontend.

### What needs work
- During iteration, it was possible to believe a new image had been deployed while the service was still serving an older revision. Clearer revision/image visibility during rapid iteration would reduce debugging time.
- More prominent deployment-state feedback would help distinguish image-build issues from service-update issues.

### Onboarding experience
Container deployment was manageable once the ECR → ECS flow was established. The hardest part was not initial deployment, but verifying that the exact intended image revision was live.

### Would I build with it again?
**Yes.**

It is a good fit for a public MCP server that needs a normal container runtime and stable HTTPS endpoint.

---

## 3. Amazon ECR

### What I used it for
ECR stores versioned Relay container images used by the ECS deployment.

### What worked well
- Straightforward integration with ECS.
- Immutable/tagged builds helped separate working versions from experimental builds.
- Useful for reproducing the exact server deployed to the public endpoint.

### What needs work
- During rapid hackathon iteration, stronger visual linking between an ECS deployment and the exact ECR image digest would reduce accidental version confusion.

### Onboarding experience
Simple once AWS authentication and Docker credentials were configured.

### Would I build with it again?
**Yes.**

---

## 4. Amazon DynamoDB

### What I used it for
Relay uses DynamoDB for durable execution state.

Tables:
- `RelayTasks`
- `RelayAudit`

`RelayTasks` stores the user contract and workflow state. `RelayAudit` stores decision and lifecycle events.

### What worked well
- Durable state survives process restarts and delayed execution.
- Low operational overhead suited a hackathon.
- The key-value/document model maps naturally to agent task state.
- It made it possible to restore state after EventBridge/Lambda resume.

### What needs work
- For debugging complex state machines, an easier task-history view across related records would help.
- Production systems would need stronger indexing, TTL/retention policies and per-user authorization.

### Onboarding experience
Fast for basic reads/writes. The main design work was deciding what should be part of task state versus the audit trail.

### Would I build with it again?
**Yes.**

It was one of the most important services in Relay because the project is specifically about surviving beyond conversational memory.

---

## 5. Amazon EventBridge Scheduler

### What I used it for
EventBridge Scheduler creates a future wake-up for a persisted Relay task.

Workflow:

```text
WAIT_SCHEDULED
      ↓
EventBridge Scheduler
      ↓
future trigger
      ↓
AWS Lambda
```

### What worked well
- Scheduling is external to the application process.
- The task can resume even if the original UI or server process is no longer holding an in-memory timer.
- It cleanly demonstrates durable time-based agent execution.

### What needs work
- IAM requirements across Scheduler and Lambda can be difficult to reason about during first setup.
- A dedicated end-to-end reference architecture for "persist → schedule → restore" agent workflows would reduce setup time.

### Onboarding experience
The API itself was straightforward, but IAM and role configuration took significantly more effort than the scheduling logic.

### Would I build with it again?
**Yes.**

This service is central to the project's durable resume story.

---

## 6. AWS Lambda

### What I used it for
`RelayResumeWorker` is invoked by EventBridge Scheduler.

The worker:
1. receives the scheduled task identifier,
2. loads persisted task state,
3. writes `RESUME_TRIGGERED`,
4. restores state,
5. writes `STATE_RESTORED`,
6. resumes the task,
7. writes `TASK_RESUMED`.

### What worked well
- Event-driven execution fits delayed task continuation.
- No always-running resume worker is required.
- Easy to connect to EventBridge.

### What needs work
- Packaging and IAM errors can look similar during debugging.
- Better cross-service diagnostics between Scheduler, Lambda and DynamoDB would improve developer experience.

### Onboarding experience
The Lambda function itself was simple; most friction was in permissions and event wiring.

### Would I build with it again?
**Yes.**

---

## 7. AWS IAM

### What I used it for
IAM controls permissions between:
- ECS and AWS resources,
- EventBridge Scheduler and Lambda,
- Lambda and DynamoDB,
- development credentials and deployments.

### What worked well
- Fine-grained roles allow the durable resume path to be separated by responsibility.

### What needs work
- IAM was one of the highest-friction areas.
- Error messages often require developers to infer which principal, trust policy or resource permission is missing.
- Workflow-specific policy examples would help.

### Onboarding experience
Moderate to difficult. It required repeated validation of trust relationships and service permissions.

### Would I build with it again?
**Yes**, because it is necessary, but I would start from narrower reference policies next time.

---

## 8. Amazon Bedrock

### What I used it for
Relay includes an optional model-orchestration layer using Amazon Bedrock.

Model configuration used by the project:

```text
openai.gpt-oss-20b
```

Bedrock is not responsible for Relay's safety-critical decisions. The primary demo path directly invokes Relay's MCP tools, while deterministic policy controls:
- budget checks,
- deadline checks,
- excluded-day checks,
- approval requirements,
- provider revalidation,
- recovery transitions.

### What worked well
- It provides a managed model endpoint for optional agent/model orchestration.
- Keeping model orchestration separate from deterministic execution made the architecture easier to reason about.

### What needs work
- Developers benefit from clearer guidance showing when a model should orchestrate versus when logic should remain deterministic.
- More reference examples combining Bedrock with MCP-style tool servers would be useful.

### Onboarding experience
Moderate. Model invocation was not the hardest part; the important design decision was defining what the model was *not allowed* to decide.

### Would I build with it again?
**Yes.**

I would continue using the model for flexible reasoning/orchestration while keeping authorization and hard constraints in deterministic code.

---

## 9. React + Vite

### What I used it for
A simulated Alexa+-style web experience demonstrating the durable delegation lifecycle.

### What worked well
- Fast iteration.
- Easy to make approval, recovery and resume states visually explicit.

### What needs work
- The current polished UI demonstrates the main service-delegation lifecycle but does not visually expose the complete HomeOps asset/warranty flow. That HomeOps capability is validated directly against the public MCP backend.

### Onboarding experience
Straightforward.

### Would I build with it again?
**Yes.**

---

## 10. Node.js Bridge

### What I used it for
The bridge connects the React demo surface to the remote Relay MCP backend.

### What worked well
- Keeps browser/UI concerns separate from MCP backend behavior.
- Made the frontend easier to iterate without changing the Python service.

### What needs work
- Cross-environment development between Windows and WSL introduced avoidable local-process friction.

### Onboarding experience
Simple technically, with more friction from local environment boundaries than from Node itself.

### Would I build with it again?
**Yes.**

---

# AWS Builder Mini-Challenge Summary

Relay uses AWS as a real execution substrate, not as a decorative integration.

The durable lifecycle is:

```text
Public MCP Server
Amazon ECS Express
        ↓
Amazon DynamoDB
        ↓
Amazon EventBridge Scheduler
        ↓
AWS Lambda
        ↓
Amazon DynamoDB
        ↓
restored task state
```

Amazon Bedrock is also integrated as an optional model-orchestration layer.

The most important AWS contribution is the **durable resume architecture**: a task can leave the immediate conversation, wait, and later continue from persisted state.

---

# Final Feedback

The strongest developer experience came from services that mapped cleanly to one responsibility:
- ECS Express → host the MCP server
- DynamoDB → durable state
- EventBridge Scheduler → future wake-up
- Lambda → resume worker

The largest friction came from:
- IAM relationships,
- verifying exact deployed image revisions,
- multi-service debugging,
- MCP SDK field naming differences.

I would build with this stack again because it provides a practical foundation for agent workflows that must survive beyond a single model response.
