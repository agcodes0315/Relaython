# Relay Shield — Operations Guide

How to configure, run, deploy and check Relay Shield, and what to do when
something goes wrong.

- [Configuration](#1-configuration)
- [Run it locally](#2-run-it-locally)
- [Run the UI](#3-run-the-ui)
- [Deploy](#4-deploy)
- [After every deployment](#5-after-every-deployment)
- [Where to look when something is wrong](#6-where-to-look)
- [Troubleshooting](#7-troubleshooting)
- [Cleaning up test data](#8-cleaning-up-test-data)

## 1. Configuration

The code does not load `.env` files by itself. Copy `.env.example` to `.env`,
fill it in, and export it:

```bash
cp .env.example .env
set -a; source .env; set +a
```

| Variable | Used by | Default | Notes |
|---|---|---|---|
| `RELAY_SHIELD_SECRET` | Server | none, **required** | The key approval codes are derived from. Use a long random value: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Without it, alerting and deciding fail closed. Never commit it. |
| `RELAY_PUBLIC_HOST` | Server | empty (localhost only) | Deployed hostname(s), comma-separated. Required on a deployed host or real requests get HTTP 421. |
| `OPENAI_API_KEY` | Bedrock classifier, optional agent | none | Optional. Without it `analyze_message` uses the rules only. Never commit it. |
| `OPENAI_BASE_URL` | Same | `https://bedrock-mantle.us-west-2.api.aws/v1` | Bedrock OpenAI-compatible endpoint |
| `RELAY_MODEL` | Same | `openai.gpt-oss-20b` | Model used for the second opinion |
| `AWS_REGION` | Server, scheduler, Lambda | `us-west-2` | |
| `RELAY_TASKS_TABLE` | Server, Lambda | `RelayTasks` | Cases are stored here |
| `RELAY_AUDIT_TABLE` | Server, Lambda | `RelayAudit` | Events are stored here |
| `RELAY_SCHEDULER_ROLE` | Scheduler | `RelaySchedulerInvokeRole` | Role EventBridge uses to call the Lambda |
| `RELAY_RESUME_LAMBDA` | Scheduler, `build_lambda.sh` | `RelayResumeWorker` | |
| `RELAY_DEPLOY_REGION` | `build_lambda.sh` only | `us-west-2` | Region for `DEPLOY=1`. A stray `AWS_REGION` does **not** redirect the deploy. |
| `DEPLOY` | `build_lambda.sh` only | unset | Set to `1` to upload the zip |
| `RELAY_MCP_URL` | End-to-end tests | the deployed service | Point tests at another server |

## 2. Run it locally

macOS or Linux, from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

export RELAY_SHIELD_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python server.py
```

In a second terminal:

```bash
curl -s localhost:8000/health
```

You should see `"status":"ok"` and `"scam_shield":true`. `/health` works without
AWS. The case tools need AWS credentials and the two DynamoDB tables.

## 3. Run the UI

The UI talks to a small Node bridge, which talks to the MCP server.

```bash
cd relay-ui
npm install
node server/bridge.mjs      # terminal 1: the bridge, on port 8787
npm run dev                 # terminal 2: the UI (Vite)
```

Open the address Vite prints and switch to the Relay Shield view.

> **The bridge has the MCP server address written into the code.** In
> `relay-ui/server/bridge.mjs` the constant `MCP_URL` is set to the deployed
> service, and the port is fixed at 8787. To use the UI with a server on your
> own machine, change `MCP_URL` to `http://127.0.0.1:8000/mcp` and restart the
> bridge. A small improvement would be `process.env.MCP_URL ?? "<deployed url>"`.

## 4. Deploy

Three things are deployed: the server image on ECS, the resume Lambda, and the
configuration. Do them in this order.

### 4.1 The resume Lambda

```bash
bash scripts/build_lambda.sh                 # builds build/relay_resume_worker.zip
DEPLOY=1 bash scripts/build_lambda.sh        # builds and uploads it
```

The script keeps `handler.py` at the top level of the zip, refuses a handler
that imports `relay`, waits for the update to finish, and then compares the
function's handler setting. **The setting must be `handler.lambda_handler`.** If
it still shows an older name, the script prints the exact fix and does not
change anything itself:

```bash
aws lambda update-function-configuration --function-name RelayResumeWorker --handler handler.lambda_handler --region us-west-2
```

Until the setting matches, scheduled wake-ups fail to import the handler. Do the
upload and the setting change back to back.

### 4.2 The server image on ECS

1. Build and push the image to your registry (ECR). If you build on an Apple
   Silicon Mac, check the architecture of your ECS task first and build for it,
   for example `docker build --platform linux/amd64 -t relay-mcp:<tag> .`.
2. In the ECS task definition, set:
   - `RELAY_PUBLIC_HOST` to the service's public hostname (plain environment
     value)
   - `RELAY_SHIELD_SECRET` as a **secret**
   - `OPENAI_API_KEY` as a **secret** (optional; without it the rules run alone)
3. Update the service to the new task definition revision.

The image installs `requirements-docker.txt` only (`mcp`, `boto3`, `botocore`,
`openai`). `openai` is imported lazily, so a missing key or package never breaks
the tool.

### 4.3 Permissions

The policy files are in `infra/iam/`. In plain words:

| Role | Needs |
|---|---|
| ECS task role | DynamoDB `GetItem`, `PutItem`, `UpdateItem`, `Query` on `RelayTasks` and `RelayAudit`; Scheduler `CreateSchedule`, `DeleteSchedule`, `GetSchedule` on schedules named `relay-resume-*`; `iam:GetRole`, `iam:PassRole` for the scheduler role; `lambda:GetFunction` for the resume Lambda |
| Lambda role | DynamoDB `GetItem`, `PutItem`, `UpdateItem`, `Query` on the same two tables |
| Scheduler role | `lambda:InvokeFunction` on `RelayResumeWorker` |

The case service and the Lambda use **conditional updates**, so `UpdateItem` is
required on both roles. Timers must be named `relay-resume-…`: the Relay Shield
names (`relay-resume-<case id>-e1`, `-exp`) already are.

## 5. After every deployment

`/health` answers 200 for **any** Host header, so a missing `RELAY_PUBLIC_HOST`
still looks healthy. Always test the real endpoint:

```bash
BASE=https://<your-service-hostname>
curl -s "$BASE/health"
```

Then check that `/mcp` accepts your host (200) and rejects another (421):

```bash
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}'
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE/mcp" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d "$INIT"
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE/mcp" -H 'Host: evil.example.com' -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d "$INIT"
```

Then run the whole story, and check the Lambda setting:

```bash
python tests/e2e/test_scam_public.py
aws lambda get-function-configuration --function-name RelayResumeWorker --query Handler --output text --region us-west-2
```

The Lambda setting must print `handler.lambda_handler`. Finally, open the logs of
the ECS service and the Lambda after a demo run and confirm they contain **no
message text and no approval code**.

## 6. Where to look

| Question | Look at |
|---|---|
| What happened to a case? | `get_case_receipt`, or the `RelayAudit` table (partition key `task_id` = the case id) |
| Where is a case right now? | `get_protection_case`, or the `RelayTasks` item |
| Did a timer fire? | The Lambda's logs (lines like `Relay shield wake handled: <case> ESCALATE applied`), and the audit events `ESCALATED`, `HOLD_EXPIRED`, or `ESCALATE_SKIPPED` / `EXPIRE_SKIPPED` |
| Which timers exist? | `aws scheduler list-schedules --name-prefix relay-resume-case- --region us-west-2` |
| Did a timer fail to be created? | The `timers_failed` field in the alert reply |

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Requests to the deployed server return HTTP 421 | `RELAY_PUBLIC_HOST` is missing or wrong | Set it to the exact hostname and redeploy. Check `/mcp`, not `/health`. |
| `RELAY_SHIELD_SECRET is not set` | The secret is not in the environment | Add it as a task secret (deployed) or export it (local) |
| Timers fire but the Lambda fails with an import error | The Lambda handler setting still names the old file | Set it to `handler.lambda_handler` (section 4.1) |
| A case stays `AWAITING_FAMILY` past its expiry | The expiry timer was not created (`timers_failed` above 0 in the alert reply), or the Lambda is failing | Check the Lambda logs and the schedules list. The payment is still held, never released. |
| `Case not found` for a case you just made | Wrong `owner_id` (deliberately the same reply as a missing case) | Use the owner id the case was created with |
| `Invalid approval code` then `Too many wrong codes` | Wrong code three times locks that contact | Open a new case; locked contacts do not unlock |
| `analyze_message` says `"source": "rules"` and `"model_used": false` | No `OPENAI_API_KEY`, no network to the model, or the model answered badly | Expected without a key. Set the key to enable the second opinion. |
| `No module named pytest` | The virtual environment was made before `requirements.txt` was updated | `python -m pip install -r requirements.txt` |
| `python: command not found` on macOS | The virtual environment is not active | `source .venv/bin/activate`, or use `python3` |
| `ModuleNotFoundError: No module named 'relay'` | A script was run from the wrong folder or by file path | Run from the repository root, and run scripts as modules: `python -m scripts.run_agent` |
| UI shows errors about the server | The bridge points at the deployed server, or the server is down | Check `MCP_URL` in `relay-ui/server/bridge.mjs` |

## 8. Cleaning up test data

Tests and demos create cases and schedules. Look for leftovers:

```bash
aws dynamodb scan --table-name RelayTasks --region us-west-2 \
  --expression-attribute-names '{"#k":"kind"}' \
  --expression-attribute-values '{":v":{"S":"scam_case"}}' \
  --filter-expression '#k = :v' --projection-expression 'task_id'

aws scheduler list-schedules --name-prefix relay-resume-case- --region us-west-2
```

A one-time schedule deletes itself after it runs. The integration tests delete
their own cases. Remove other demo cases only if you no longer need their audit
trails.
