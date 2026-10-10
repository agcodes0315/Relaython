# Relay — Hackathon Friction Log

## 1. Recovery weakened original contract
**Task attempted:** Recover after provider failure.  
**Steps taken:** Simulated failure and re-ranked alternatives.  
**Expected result:** Only options satisfying the original contract should remain.  
**Actual result:** An invalid replacement could reappear in an early implementation.  
**Severity:** High.  
**Workaround:** Reapplied persisted constraints before every recovery proposal.  
**Actionable suggestion:** Provide first-class constraint-revalidation primitives.

## 2. Approval became stale after provider failure
**Task attempted:** Continue after an approved provider failed.  
**Steps taken:** Approved one provider, failed it, then selected a replacement.  
**Expected result:** Previous consent should not authorize a different action.  
**Actual result:** A naïve flow can treat approval as reusable permission.  
**Severity:** High.  
**Workaround:** Added context-bound approval and explicit invalidation.  
**Actionable suggestion:** Model approval scope/invalidation as a first-class workflow primitive.

## 3. ECS briefly served an older tool surface
**Task attempted:** Deploy the latest HomeOps MCP image.  
**Steps taken:** Built/pushed image and updated ECS.  
**Expected result:** Public endpoint exposes the latest tools.  
**Actual result:** Service temporarily reflected an older revision.  
**Severity:** Medium.  
**Workaround:** Verified tags/digests and redeployed intended revision.  
**Actionable suggestion:** Make active image digest/revision more prominent.

## 4. MCP Python SDK naming mismatch
**Task attempted:** Validate resource templates.  
**Steps taken:** Used camelCase assumptions.  
**Expected result:** Template metadata should be directly readable.  
**Actual result:** Python SDK exposed snake_case (`resource_templates`, `uri_template`).  
**Severity:** Low/Medium.  
**Workaround:** Updated client field access.  
**Actionable suggestion:** Document protocol-to-SDK field mapping.

## 5. EventBridge + Lambda + IAM durable resume setup
**Task attempted:** Resume a persisted task later.  
**Steps taken:** Configured scheduler, Lambda, permissions and state restoration.  
**Expected result:** EventBridge invokes Lambda and task restores.  
**Actual result:** Multiple trust/permission relationships had to align.  
**Severity:** Medium.  
**Workaround:** Validated each component independently.  
**Actionable suggestion:** Publish an ECS + DynamoDB + EventBridge + Lambda reference architecture.

## 6. Bedrock invocation restriction
**Task attempted:** Validate optional model orchestration in Playground.  
**Steps taken:** Selected gpt-oss-20b and another supported model.  
**Expected result:** Model responds in Playground.  
**Actual result:** Console returned `ValidationException: Operation not allowed`.  
**Severity:** Low/Medium because Bedrock is optional.  
**Workaround:** Kept core Relay safety and execution independent of Bedrock.  
**Actionable suggestion:** Surface account-level invocation restrictions clearly.

## 7. Windows + WSL environment friction
**Task attempted:** Run frontend/bridge and backend/AWS tooling.  
**Steps taken:** Used WSL for frontend and Windows PowerShell for backend/AWS.  
**Expected result:** Predictable local startup.  
**Actual result:** Shell/path differences increased setup time.  
**Severity:** Low.  
**Workaround:** Documented shell-specific startup commands.  
**Actionable suggestion:** Provide one cross-platform local simulator/startup command.

## 8. HomeOps backend stronger than visual coverage
**Task attempted:** Demonstrate asset, warranty, troubleshooting and service preparation.  
**Steps taken:** Implemented and publicly validated MCP capabilities.  
**Expected result:** Full journey is visible in polished UI.  
**Actual result:** UI emphasized delegation/approval/recovery/resume.  
**Severity:** Medium for demo clarity.  
**Workaround:** Added backend proof and this HomeOps UI improvement component.  
**Actionable suggestion:** Provide a lightweight visual simulator for self-hosted MCP workflows.
