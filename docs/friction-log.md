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

## 9. DynamoDB reserved word `status` in conditional updates
**Task attempted:** Change a case's status only if it is still in the expected state.  
**Steps taken:** Wrote conditional update expressions that name `status` and nested approval fields.  
**Expected result:** The expression reads like the data model.  
**Actual result:** `status` is a DynamoDB reserved word, and nested paths need a name placeholder for every part.  
**Severity:** Low.  
**Workaround:** Used `#s` for `status` and one placeholder per path part, and added tests that check the generated expressions.  
**Actionable suggestion:** Offer a linter or clearer error that names the reserved word and the placeholder fix.

## 10. `/health` looked fine while the real endpoint rejected requests
**Task attempted:** Check a new deployment.  
**Steps taken:** Called `/health` after deploying without `RELAY_PUBLIC_HOST`.  
**Expected result:** A healthy check means the service accepts real requests.  
**Actual result:** `/health` answers 200 for any Host header, while `/mcp` returned HTTP 421 for the public hostname.  
**Severity:** Medium.  
**Workaround:** Always test `/mcp` for 200 (allowed host) and 421 (unlisted host) after a deployment, and documented the check.  
**Actionable suggestion:** Let a health check run against the same host rules as the main endpoint, or warn when the public host is not configured.

## 11. The Lambda handler setting must match the packaged file
**Task attempted:** Redeploy the resume Lambda with Relay Shield escalation.  
**Steps taken:** Packaged and uploaded a new zip.  
**Expected result:** The new code runs on the next timer.  
**Actual result:** The function's handler setting is separate from the zip. If it names an older file, scheduled wake-ups fail to import the handler.  
**Severity:** Medium.  
**Workaround:** `scripts/build_lambda.sh` now compares the handler setting after the upload and prints the exact fix command.  
**Actionable suggestion:** Warn at upload time when the handler setting does not match a file in the package.

## 12. Creating a timer also rewrote the task record
**Task attempted:** Create escalation and expiry timers for a case.  
**Steps taken:** Used the existing scheduler helper, which saves the task record as part of creating a timer.  
**Expected result:** Creating a timer only creates a timer.  
**Actual result:** With the server and the Lambda both writing a case, saving the whole record could overwrite a newer status.  
**Severity:** High.  
**Workaround:** Added a `persist_task=False` option so Relay Shield timers never rewrite the case, and a test that old callers behave as before.  
**Actionable suggestion:** Document which writes a scheduling helper makes, and show a pattern for two writers sharing one record.

## 13. The demo UI bridge had the server address written into the code
**Task attempted:** Run the UI against a server on my own machine.  
**Steps taken:** Started the bridge and the UI locally.  
**Expected result:** The UI talks to the local server.  
**Actual result:** `MCP_URL` in the bridge pointed at the deployed service, so the UI showed 17 tools and old behavior.  
**Severity:** Medium.  
**Workaround:** Documented the constant and the change to make.  
**Actionable suggestion:** Read the address from an environment variable and print the target on startup.

## 14. Tests that passed only on the author's machine
**Task attempted:** Run the full unit suite on a clean Linux machine.  
**Steps taken:** Created a new virtual environment and ran `python -m pytest`.  
**Expected result:** All tests pass.  
**Actual result:** 12 tests failed because a test started bash from a Windows path, and another compared hashes of Python's `ast.dump()` output, which can differ between Python versions.  
**Severity:** Medium.  
**Workaround:** Used the normal `bash` outside Windows and fingerprinted each tool's source text, with a test that proves a real edit is still caught.  
**Actionable suggestion:** Run the unit tests in CI on Linux and Windows.

## 15. Python version differed between local and the container
**Task attempted:** Keep local runs and the deployed image consistent.  
**Steps taken:** Developed in a newer Python virtual environment while the Docker image uses Python 3.12.  
**Expected result:** The same behavior in both.  
**Actual result:** Dependencies resolved to different versions locally than in the image.  
**Severity:** Low.  
**Workaround:** Kept the runtime dependencies in `requirements-docker.txt` and ran the unit suite on Python 3.12 for review.  
**Actionable suggestion:** Pin the Python version and dependency versions for the project, and test the image's versions in CI.
