# Relay — Hackathon Friction Log

This log records real implementation friction encountered while building Relay.

Each entry follows:
- Task attempted
- Steps taken
- Expected result
- Actual result
- Severity
- Workaround
- Actionable suggestion

---

## Entry 1 — Recovery accidentally weakened the original contract

### Task attempted
Recover automatically when the originally selected provider became unavailable.

### Steps taken
1. Created a task with:
   - budget ≤ ₹2,000
   - deadline 10 Oct 2026
   - Thursday excluded
2. Selected and approved QuickFix.
3. Simulated provider failure.
4. Started recovery.
5. Generated replacement provider options.

### Expected result
Recovery should reapply every original constraint before proposing a replacement.

### Actual result
An early implementation allowed PremiumAir, priced at ₹2,600, to reappear during recovery even though the user had explicitly set a ₹2,000 maximum.

### Severity
**High**

The bug violated a core user constraint during a failure path.

### Workaround / fix
Recovery was changed so that it:
1. invalidates the old approval,
2. re-runs provider filtering,
3. reapplies budget, deadline and excluded weekday constraints,
4. requires fresh human approval for the replacement.

A regression test was added.

### Actionable suggestion
Agent workflow frameworks should treat recovery as a new policy-evaluation boundary rather than simply continuing from the last successful step.

---

## Entry 2 — Consent remained meaningful only if tied to execution context

### Task attempted
Reuse an already-approved workflow after a provider failure.

### Steps taken
1. User approved QuickFix at ₹1,800.
2. QuickFix was marked unavailable.
3. Recovery proposed another provider.

### Expected result
The system should recognize that approval for QuickFix does not authorize a different provider or changed commitment.

### Actual result
The initial state model did not make approval invalidation explicit enough.

### Severity
**High**

Reusing stale consent can create unsafe or misleading agent behavior.

### Workaround / fix
Approval became context-bound:
- provider failure invalidates the previous approval,
- recovery writes an invalidation event,
- any replacement commitment requires fresh approval.

### Actionable suggestion
Agent frameworks should provide first-class patterns for approval scope, invalidation and re-approval.

---

## Entry 3 — ECS deployment appeared updated while an older server image was still live

### Task attempted
Deploy the HomeOps-expanded MCP server.

### Steps taken
1. Added HomeOps tools.
2. Built a container image.
3. Updated the ECS service.
4. Queried the public MCP server.

### Expected result
The public server should expose the newly added MCP tools.

### Actual result
The live service initially still exposed the older tool surface.

### Severity
**Medium**

The application was available, but validation was testing the wrong deployed revision.

### Workaround / fix
The HomeOps changes were confirmed inside `server.py`, a new container image was built and tagged, pushed to ECR, and ECS was updated until the new deployment reached steady state.

### Actionable suggestion
ECS deployment views should make the running image tag/digest more prominent and easier to compare with the image a developer just pushed.

---

## Entry 4 — MCP Python SDK field names differed from protocol-style camelCase

### Task attempted
Validate public MCP Resources and Resource Templates using the Python MCP client.

### Steps taken
1. Called `list_resource_templates`.
2. Accessed `resourceTemplates`.
3. Accessed `uriTemplate`.

### Expected result
The test script should print the available resource template.

### Actual result
The installed SDK exposed Pydantic fields as:
- `resource_templates`
- `uri_template`

The original camelCase accesses raised `AttributeError`.

### Severity
**Low / Medium**

The backend was healthy, but the public validation script failed.

### Workaround / fix
Updated the test client to use the SDK's snake_case Python properties.

The public HomeOps MCP validation then passed.

### Actionable suggestion
SDK documentation should explicitly show protocol JSON names alongside language-native object property names.

---

## Entry 5 — EventBridge Scheduler + Lambda + IAM required cross-service debugging

### Task attempted
Schedule a Relay task to wake later and resume from DynamoDB.

### Steps taken
1. Persisted the task.
2. Created an EventBridge schedule.
3. Configured the Scheduler execution role.
4. Configured Lambda.
5. Granted DynamoDB permissions.
6. Ran a delayed public resume test.

### Expected result
EventBridge should invoke Lambda and Lambda should restore the persisted task.

### Actual result
Getting all trust relationships and permissions correct required several iterations.

### Severity
**Medium**

The workflow could not complete until all roles and permissions were correct.

### Workaround / fix
Separated responsibilities:
- scheduler role → invoke Lambda,
- Lambda role → read/write DynamoDB,
- ECS role → create/manage schedule state as needed.

Validated the final path using audit events:
- `WAIT_SCHEDULED`
- `RESUME_TRIGGERED`
- `STATE_RESTORED`
- `TASK_RESUMED`

### Actionable suggestion
AWS documentation would benefit from a compact "durable agent wait/resume" reference architecture with sample trust policies for Scheduler → Lambda → DynamoDB.

---

## Entry 6 — AWS authentication flow interrupted rapid iteration

### Task attempted
Continue AWS deployment/testing after credentials or session state expired.

### Steps taken
1. Ran AWS CLI commands.
2. Authentication/session state was no longer valid.
3. Re-entered the AWS login flow.

### Expected result
A quick renewal path back to the same working CLI session.

### Actual result
The authentication flow interrupted deployment/debugging and required careful handling of verification steps.

### Severity
**Low / Medium**

No application bug, but significant iteration friction.

### Workaround
Re-authenticated and resumed using the configured AWS CLI installation and region.

### Actionable suggestion
CLI messaging should more clearly separate:
- the URL the user opens,
- the verification code,
- the account/session being refreshed.

---

## Entry 7 — Windows + WSL process boundaries caused frontend startup friction

### Task attempted
Run the Node bridge and Vite frontend while developing from a Windows repository.

### Steps taken
1. Ran Linux commands from PowerShell.
2. Commands using `||`, `nohup`, `sudo` and `&` failed because they were Bash syntax.
3. Moved the frontend workflow into native WSL.

### Expected result
The frontend bridge and Vite server should start normally.

### Actual result
Shell mismatch produced parser errors.

### Severity
**Low**

No product defect, but confusing during fast iteration.

### Workaround
Kept:
- Python/AWS/Git commands in PowerShell,
- Node/Vite bridge workflow in WSL/Bash.

### Actionable suggestion
Cross-platform setup guides should label command blocks explicitly as PowerShell, Bash, or WSL rather than only "terminal".

---

## Entry 8 — HomeOps backend capability exceeded the current visual demo surface

### Task attempted
Demonstrate the full HomeOps path from:
"Alexa, my AC isn't cooling properly."

### Steps taken
1. Added public MCP tools for:
   - household assets,
   - warranty checks,
   - safe troubleshooting,
   - service preparation.
2. Entered the HomeOps phrase into the simulated Alexa+ UI.

### Expected result
The UI should visually walk through asset discovery, warranty and troubleshooting.

### Actual result
The polished frontend still routes into the older service-delegation/provider flow.

### Severity
**Medium (demo clarity)**

The backend functionality works, but the visual demo does not expose every HomeOps capability.

### Workaround
Validated the HomeOps capabilities directly against the public MCP server with `test_homeops_public.py`, including:
- `list_household_assets`
- `check_warranty`
- `troubleshoot_home_asset`
- `prepare_service_from_asset`

The README explicitly distinguishes the backend capability from the frontend demo.

### Actionable suggestion
Agent platforms should make it easier to generate or bind UI surfaces directly from MCP tool/resource outputs.

---

# Summary

The most important friction was not syntax or setup. It was discovering that **failure recovery is a new safety boundary**.

The strongest design improvements came directly from these failures:

```text
provider failure
      ↓
invalidate stale approval
      ↓
reapply original contract
      ↓
filter replacements
      ↓
require fresh approval
```

This became one of Relay's core safety properties.
