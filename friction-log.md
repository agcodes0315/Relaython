🧱 Relay Development Friction Log
Developer Experience Notes from Building Relay
This document records concrete development friction encountered while building Relay with MCP, AWS, Docker, WSL, and a durable task architecture.
The goal is to document not only what failed, but also:
- what was expected
- what actually happened
- the workaround used
- how the developer experience could be improved
1. MCP Python SDK Version Mismatch
Date: October 5, 2026
Tool / API / SDK: MCP Python SDK
Severity: Low
Task Attempted
Run the first Relay MCP server.
Expected Result
The server should start successfully after installing the MCP package.
Actual Result
Older examples referenced FastMCP, while the installed SDK exposed the newer server API using MCPServer.
Workaround
Updated the implementation to use the installed SDK API and verified the live server through MCP protocol negotiation.
Suggested Improvement
Official documentation should make the SDK major version highly visible and keep migration examples next to the primary getting-started path.
2. SDK Version vs MCP Protocol Version
Tool / API / SDK: MCP SDK / MCP Specification
Severity: Medium
Problem
It was easy to confuse:
MCP package version
with:
MCP negotiated protocol version
These are not the same thing.
Workaround
Validated the protocol directly through the live MCP client.
Relay negotiated:
2025-11-25
Suggested Improvement
Documentation should explicitly distinguish SDK release versions from MCP protocol versions.
3. Docker Desktop Credential Helper Blocked ECR Push
Tool / API / SDK: Docker Desktop + Amazon ECR
Severity: Medium
Expected Result
Authenticate Docker to ECR and push the image normally.
Actual Result
The local Docker credential helper failed even though AWS authentication was valid.
Workaround
Created a temporary Docker configuration containing only the ECR authentication token:
docker --config <temporary-config> push ...
The temporary credential directory was deleted immediately afterward.
Suggested Improvement
AWS/ECR documentation should include a Windows-specific fallback for Docker credential-helper failures.
4. Initial App Runner Deployment Was Unavailable
Tool / API / SDK: AWS App Runner
Severity: Medium
Task Attempted
Deploy the public Relay MCP container.
Actual Result
The account returned a subscription-related error.
Workaround
Moved deployment to:
Amazon ECS Express
which successfully hosted the public MCP endpoint.
Suggested Improvement
Service eligibility should be surfaced earlier in the deployment workflow.
5. Reusing latest Made Stale Deployments Hard to Diagnose
Tool / API / SDK: Amazon ECR + ECS Express
Severity: High
Expected Result
Deploying a new latest image should expose the newest MCP tools.
Actual Result
The public MCP endpoint continued exposing an older server version.
Workaround
Switched to immutable, descriptive tags:
recovery-v1
recovery-v2
resume-v1
secure-v1
and inspected the container contents before deployment.
Suggested Improvement
Deployment guides should strongly recommend immutable image tags.
6. npm Failed on the Windows-Mounted WSL Filesystem
Tool / API / SDK: WSL + npm + Vite
Severity: Medium
Task Attempted
Install frontend dependencies under:
/mnt/c/...
Actual Result
npm returned filesystem permission / chmod-style errors.
Workaround
Moved the frontend to the native Linux filesystem:
/home/lenovo/relay-ui
and ran npm there.
Suggested Improvement
WSL Node documentation should prominently recommend the native Linux filesystem for dependency-heavy projects.
7. PowerShell and WSL Commands Were Easy to Mix Up
Tool / API / SDK: Windows PowerShell + WSL
Severity: Low
Examples:
cd ~/relay-ui
was accidentally run in PowerShell.
PowerShell commands such as:
Get-Content
were accidentally run in bash.
Final Workflow
Windows PowerShell
→ AWS CLI
→ Python
→ Docker
→ Git

WSL Ubuntu
→ React/Vite
→ Node MCP bridge
Suggested Improvement
Cross-platform documentation should label every command block with its intended shell.
8. Windows Browser Could Not Initially Reach WSL Localhost
Tool / API / SDK: WSL Networking + Vite
Severity: Medium
Expected Result
Open:
http://localhost:5173
from the Windows browser.
Actual Result
The Vite server was reachable inside WSL but not from the Windows-side browser.
Workaround
Started Vite with:
--host 0.0.0.0
and opened the frontend using the WSL IP address.
The frontend API was also changed to use:
window.location.hostname
so the browser could reach the local bridge on port 8787.
9. AWS Login Sessions Expired During Long Debugging Sessions
Tool / API / SDK: AWS CLI + boto3
Severity: Medium
Error
LoginRefreshRequired
Your session has expired
Workaround
Reauthenticated with:
aws login
aws sts get-caller-identity
before rerunning AWS-dependent tests.
Suggested Improvement
The CLI could provide an early warning when an interactive session is close to expiry.
10. Durable Resume Initially Deployed the Wrong Lambda Artifact
Tool / API / SDK: AWS Lambda
Severity: High
Expected Result
The updated resume worker should emit:
STATE_RESTORED
TASK_RESUMED
Actual Result
Only:
RESUME_TRIGGERED
appeared.
Repeated uploads showed the same Lambda code size/hash.
Root Cause
The local file being packaged was still the older implementation.
Workaround
Verified:
- source strings
- ZIP contents
- Lambda code size
- Lambda code hash
before redeploying.
After the correct package was uploaded, the full durable-resume sequence worked.
Suggested Improvement
Deployment tutorials should recommend verifying artifact contents and hashes before debugging downstream services.
11. Failure Recovery Exposed a Real Constraint Bug
Tool / API / SDK: Relay Recovery Logic
Severity: High
Expected Result
After provider failure, only providers satisfying the original delegation contract should remain.
Actual Result
A provider above the original ₹2,000 budget reappeared during recovery.
Workaround
Added recovery-time revalidation for:
- provider availability
- budget
- deadline
- excluded weekday
Product Lesson
Recovery must be treated as a new policy checkpoint, not simply:
pick the next provider
🧠 Main Engineering Lesson
Relay debugging repeatedly required validating the entire path:
source code
   ↓
local test
   ↓
container
   ↓
registry
   ↓
ECS deployment
   ↓
MCP tool list
   ↓
DynamoDB
   ↓
EventBridge
   ↓
Lambda
   ↓
audit trail
   ↓
frontend
A failure that appears in one layer can originate several layers earlier.
That full-chain validation process became part of the final Relay engineering workflow.