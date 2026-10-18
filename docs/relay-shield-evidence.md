# Relay Shield — Evidence

Screenshots and terminal captures that back up what the other Shield documents
claim. Judges can open each file and see the result themselves.

Save every file in `docs/images/shield/`. Use the exact file names below so the
links work. Tick the box when the file is in the repository.

- [Before you capture](#before-you-capture)
- [The captures](#the-captures)
- [Dates and numbers to fill in](#dates-and-numbers-to-fill-in)

## Before you capture

- Capture **after** the new image is deployed. A capture of the old server shows
  17 tools, not 26.
- Hide or crop: access keys, secret values, session tokens, `RELAY_SHIELD_SECRET`,
  `OPENAI_API_KEY`, and any real phone number. AWS account ids are not
  credentials, but you may blur them.
- Use real cases only. Do not edit a number in an image.
- JPEG or PNG, under 1 MB each, readable at normal zoom.
- For terminal captures, use a light or dark theme with large text, and show the
  command and its result in the same image.

## The captures

### The product

| Done | File | What it shows | What it proves |
|---|---|---|---|
| [ ] | `01-shield-analyze.jpeg` | Savita's phone after **Analyze message**: score, level and signals | The scoring works and explains itself |
| [ ] | `02-shield-hold.jpeg` | The payment assessed as HOLD, with the case opened | Policy holds a risky payment |
| [ ] | `03-shield-family-phone.jpeg` | The family panel with the one-time code | The code appears only on the family side |
| [ ] | `04-shield-receipt.jpeg` | The audit trail after a rejection, and the evidence text | Every step is recorded |
| [ ] | `05-shield-expired-blocked.jpeg` | A case that ended `EXPIRED_BLOCKED` with the payment `BLOCKED` | Silence never releases money |

### The AWS deployment

| Done | File | What it shows | What it proves |
|---|---|---|---|
| [ ] | `06-ecs-shield-task.jpeg` | The ECS service with the new task definition and the image tag | The Shield build is deployed |
| [ ] | `07-ecs-secrets.jpeg` | The task definition's secrets list, **names only** | The secrets are not plain environment text |
| [ ] | `08-dynamodb-case-item.jpeg` | A `scam_case` item in `RelayTasks` | The case is stored with a masked payee and no approval code |
| [ ] | `09-eventbridge-schedules.jpeg` | Schedules named `relay-resume-case-…-e1` and `-exp` | The timers exist |
| [ ] | `10-lambda-handler-and-logs.jpeg` | The handler setting `handler.lambda_handler` and a log line like `ESCALATE applied` | The Lambda runs, and its log has no message text or code |

### The tests

| Done | File | What it shows | What it proves |
|---|---|---|---|
| [ ] | `11-pytest-unit.png` | `python -m pytest -q` ending in `420 passed` | The unit tests pass |
| [ ] | `12-integration-real-aws.png` | `python -m tests.integration.test_scam_case` and `test_scam_lambda` passing | The case flow and the Lambda work on real AWS |
| [ ] | `13-e2e-public.png` | `python tests/e2e/test_scam_public.py` passing against the deployed URL | The whole story works through the public endpoint |
| [ ] | `14-health-and-421.png` | `/health` with `scam_shield: true`, then `/mcp` 200 and 421 | The deployment is healthy and rejects other hosts |
| [ ] | `15-tools-list-26.png` | A `tools/list` result or the bridge showing 26 tools | The new tools are live |
| [ ] | `16-bedrock-live.png` | An `analyze_message` result with `"source": "rules+model"` | The Bedrock second opinion works |
| [ ] | `17-ui-build.png` | `npm run lint` and `npm run build` | The UI builds |

## Dates and numbers to fill in

| Item | Value |
|---|---|
| Date of the real-AWS runs | |
| Image tag deployed | `relay-mcp:shield-task13` (confirm) |
| ECS task definition revision | `default-relay-mcp:21` (confirm) |
| Unit tests passed | 420 (confirm on your machine) |
| Date and result of the live Bedrock call | |

## Commands that produce the captures

```bash
# 11: unit tests
python -m pytest -q

# 14: health and host validation
BASE=https://<your-service-hostname>
curl -s "$BASE/health"
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}'
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE/mcp" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d "$INIT"
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE/mcp" -H 'Host: evil.example.com' -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d "$INIT"

# 12 and 13: real AWS
python -m tests.integration.test_scam_case
python -m tests.integration.test_scam_lambda
python tests/e2e/test_scam_public.py

# 9 and 10: timers and the Lambda setting
aws scheduler list-schedules --name-prefix relay-resume-case- --region us-west-2
aws lambda get-function-configuration --function-name RelayResumeWorker --query Handler --output text --region us-west-2

# 17: the UI
cd relay-ui && npm run lint && npm run build
```
