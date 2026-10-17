\# Relay - Amazon Developer Hackathon 2026 Submission Brief



\## One-Line Pitch



Relay is the durable execution layer that helps Alexa+ tasks survive approvals, failures, waiting, safety checks and future resume without silently weakening the user's original intent.



\## Core Problem



Conversational assistants understand requests, but real-world tasks must survive provider failures, human approval, delays, changing conditions and infrastructure restarts.



Relay moves execution state out of disposable conversational context and into a durable, auditable workflow.



\## What Relay Demonstrates



\- Remote MCP server over Streamable HTTP

\- Durable task contracts

\- Deterministic safety policy

\- Context-bound human approval

\- Constraint revalidation

\- Provider failure recovery

\- Durable wait and resume

\- DynamoDB-backed task and audit state

\- EventBridge Scheduler wake-ups

\- AWS Lambda resume execution

\- Decision receipts

\- HomeOps workflows

\- Relay Shield scam protection



\## Relay Shield



Relay Shield applies the same durable execution model to suspicious payment workflows.



A suspicious payment can be analyzed, placed on HOLD, attached to a protection case and escalated to a trusted family contact.



The assistant never receives the private approval code.



\### Safety Principle



\*\*Silence never releases money.\*\*



\## Security Hardening



The final Shield build includes:



\- wrong-owner requests behaving like missing cases

\- approval codes isolated to the family inbox

\- no fallback Shield secret

\- maximum 3 wrong approval attempts

\- maximum 5 alert attempts

\- bounded payment amounts

\- safe owner-id validation

\- message-length validation

\- approval-code isolation from audit responses

\- documented production OAuth/OIDC ownership architecture



\## AWS Architecture



Alexa+ / Demo Surface -> Amazon ECS Relay MCP -> DynamoDB -> EventBridge Scheduler -> AWS Lambda -> restored durable execution.



Amazon ECR stores the deployed container image.



\## Public MCP



https://re-4f589c522a0645c5b9f2ead60f3e7516.ecs.us-west-2.on.aws/mcp



\## Verified Deployment



\- AWS region: us-west-2

\- ECS cluster: default

\- ECS service: relay-mcp

\- Task definition: default-relay-mcp:21

\- Image: relay-mcp:shield-task13

\- Running: 1

\- Pending: 0



\## Verified Testing



\- 25 Relay Shield security tests passed

\- 420 total automated tests passed

\- real AWS case integration passed

\- real Lambda escalation and expiry integration passed

\- public MCP end-to-end Relay Shield flow passed



\## Real vs Simulated



Real: MCP backend, ECS, ECR, DynamoDB, EventBridge, Lambda, policy engine, approval state machine, audit trail and public end-to-end execution.



Simulated: Alexa+ consumer UI, household identities, providers, external payment rails and family SMS/push delivery.



\## Closing



\*\*Reasoning may be probabilistic. Authority should not be.\*\*



Alexa+ understands what the user needs. Relay preserves what they meant and makes sure the task survives the real world.

