# Relay Shield — Testing

Relay Shield is tested in four layers. This document says what each layer
proves, how to run it, and which results were reproduced independently and
which were reported by the team.

## 1. The layers

| Layer | Needs AWS? | What it proves | Where |
|---|---|---|---|
| Unit tests | No | Logic, limits, state machine, the Lambda handler (with fake tables), the build script, source-level guards | `tests/unit/` |
| Integration tests | Yes | The case flow and the Lambda against real DynamoDB, Scheduler and Lambda | `tests/integration/` |
| End-to-end tests | A running server | The whole story through the public MCP endpoint | `tests/e2e/` |
| UI checks | No | The React app lints and builds | `relay-ui/` |

Test style: plain pytest functions with plain `assert`, no network, no AWS in the
unit layer. Tests describe behavior in their names.

## 2. Unit tests

`python -m pytest` runs the unit tests (`pytest.ini` sets `testpaths = tests/unit`
and `pythonpath = .`). There are 358 test functions in 24 files, collected as
**420 tests** because some are parametrized. 23 of the original tests existed
before Relay Shield.

| File | Functions | Covers |
|---|---|---|
| `test_scam_scoring.py`, `test_scam_scoring_edge.py` | 15, 28 | Signals and weights, boundaries 24/25/49/50/74/75 and 39/40/69/70, the cap at 100, the OTP-plus-impersonation rule, false positives (real bank OTP texts), robustness, masking, monotonic scoring, number handling |
| `test_scam_policy.py`, `test_scam_policy_edge.py` | 15, 29 | The full 81-pair transition matrix, a hand-written 60-case payment decision table, invalid input, action names, contact ordering |
| `test_scam_tokens.py`, `test_scam_tokens_edge.py` | 18, 18 | Approval code format, determinism, verification, hostile input, expiry boundary |
| `test_scam_service.py`, `test_scam_service_edge.py` | 10, 9 | Opening cases, conditional-update expressions, masking, clamping, owner checks |
| `test_scam_family.py` | 24 | Alert once, timers, correct and wrong codes, lockout, replay, expiry, inbox rules, code never leaves the inbox |
| `test_scam_receipt.py`, `test_scam_receipt_edge.py` | 6, 20 | Receipt content, secret removal at every depth, ordering, purity, JSON safety |
| `test_scam_classifier.py`, `test_scam_classifier_edge.py` | 8, 32 | Bedrock parsing, fallbacks, the model can only raise the score, injection, truncation, no logging of content |
| `test_scam_security.py` | 16 | Owner id and amount validation, same reply for wrong owner and missing case, fail-closed secret, length limits, attempt and alert limits |
| `test_scam_server_surface.py` | 16 | 26 tools with the right signatures, resources and prompts, health flag, the original 17 tools unchanged, the agent layer never given family tools |
| `test_scheduler_names.py`, `test_scheduler_resume_edge.py` | 7, 9 | Timer names and payloads, and that old callers behave exactly as before |
| `test_lambda_scam_branch.py`, `test_lambda_scam_edge.py` | 7, 35 | ESCALATE and EXPIRE, idempotency, wrong states, odd input, "the Lambda never releases a payment" |
| `test_lambda_build_script.py` | 13 | `scripts/build_lambda.sh` in a temporary folder with a fake `aws` command |
| `test_homeops.py`, `test_improvement_guards.py`, `test_preflight.py`, `test_relay_safety.py` | 7, 4, 6, 6 | The original Relay behavior |

Shared helpers (not tests): `tests/unit/lambda_fakes.py` (in-memory DynamoDB
tables that honor the conditions the Lambda uses, and a loader for the handler)
and `tests/unit/scam_fakes.py`.

Expectations in the policy and Lambda tests are written by hand rather than read
from the code, so changing a rule makes a test fail. During development the
scoring, policy and Lambda tests were checked with deliberate breakages
("mutation checks"): removing a condition, writing a released status, printing
the whole event, and similar, and a test failed each time.

### Run

```bash
# from the repository root, with the virtual environment active
python -m pip install -r requirements.txt
python -m pytest                       # all unit tests
python -m pytest tests/unit/test_lambda_scam_edge.py -v
```

On macOS the command is `python` inside the virtual environment and `python3`
outside it.

## 3. Integration tests (need AWS)

These need AWS credentials and the `RelayTasks` and `RelayAudit` tables. Run them
as modules from the repository root.

```bash
python -m tests.integration.test_scam_case      # case flow on real DynamoDB and Scheduler
python -m tests.integration.test_scam_lambda    # invokes the real RelayResumeWorker
python -m tests.integration.test_dynamodb
python -m tests.integration.test_recovery
python -m tests.integration.test_scheduler
```

`test_scam_case` opens a HOLD case, checks the alert is idempotent, rejects a
wrong code, reads the code from the inbox, approves, and checks a second
decision is refused and the audit trail is complete.

## 4. End-to-end test

```bash
python tests/e2e/test_scam_public.py
```

It connects to the MCP endpoint (default: the deployed service; set
`RELAY_MCP_URL` to test another one), runs the full story through tool calls,
waits for the real escalation timer (about a minute or two, with a countdown),
rejects as the second contact, reads the receipt, and checks that approval codes
appear **only** in `get_family_inbox` replies. The other end-to-end scripts
(`test_mcp_http.py`, `test_homeops_public.py`, `test_recovery_public.py`,
`test_resume_public.py`) test the deployed errand and HomeOps flows; they show
the version that is live, not your local code.

## 5. UI checks

```bash
cd relay-ui
npm install
npm run lint
npm run build
```

The UI has no JavaScript test runner and no automated browser test. The rule
that the approval code is shown only in the family-phone panel is checked by
hand during the demo run (see [relay-shield-demo-script.md](./relay-shield-demo-script.md)),
and the server side of the rule (the code appears only in `get_family_inbox`
replies) is covered by the unit and end-to-end tests above.

## 6. Verification record

### Reproduced in a review of the repository

Environment: Linux, Python 3.12, a clean virtual environment, October 2026.

| Check | Result |
|---|---|
| Unit tests (`python -m pytest`) | **420 passed** |
| Original 17 tools unchanged | Confirmed. A deliberate edit to an original tool makes `test_original_tools_are_unchanged` fail |
| Server start and `/health` | `"scam_shield": true` |
| `/mcp` host validation | 200 for an allowed host, **421** for an unlisted host |
| `npm run lint` | 0 errors, 3 warnings (unused code and one effect rule, none in Shield logic) |
| `npm run build` | Succeeds |

### Reported by the team, with evidence

According to `docs/SUBMISSION_BRIEF.md`, these were run against the deployed
service in us-west-2 (image `relay-mcp:shield-task13`): the real AWS case
integration test, the real Lambda escalation and expiry integration test, and
the public MCP end-to-end flow.

The captures that back this up are listed in
[relay-shield-evidence.md](./relay-shield-evidence.md).

## 7. Portability fixes

Two tests used to pass only on the machine that wrote them. Both are fixed in
the repository:

- `test_lambda_build_script.py` started bash with the Windows path
  `C:\Program Files\Git\bin\bash.exe`, so it failed on every Mac and Linux
  machine (12 failures). It now uses Git Bash on Windows and the normal `bash`
  elsewhere.
- `test_original_tools_are_unchanged` compared stored hashes of Python's
  `ast.dump()` output, which can change between Python versions. It now
  fingerprints each tool's source text, which is the same everywhere. The test
  still fails if an original tool is edited.

## 8. Known gaps

- Real-AWS and live-Bedrock results are reported by the team. The review above
  reproduced the offline checks only.
- There is no local imitation of AWS in the repository, so the integration and
  end-to-end tests need a real AWS account.
- The UI has no automated test, so the family-phone-only display of the approval code is checked by hand.
- There is no load or latency test of the Relay Shield path.
- Timers are exercised with a 2-minute hold; a full 30-minute hold was not run.
