# Relay Shield — Tool Reference

Relay Shield adds **9 MCP tools, 1 resource and 1 prompt** to the Relay server
(26 tools in total with the original 17). All of them are served over
Streamable HTTP at the server's `/mcp` endpoint.

The example replies below are real output from the running system, with case
ids, times and the approval code replaced by placeholders.

- [Tool summary](#tool-summary)
- [Typical call order](#typical-call-order)
- [Tools](#tools)
- [Resource and prompt](#resource-and-prompt)
- [Error messages](#error-messages)
- [Limits](#limits)
- [Which tools an assistant may use](#which-tools-an-assistant-may-use)

## Tool summary

| Tool | Risk tier | Changes anything? | Who should call it |
|---|---|---|---|
| `analyze_message` | READ_ONLY | No | Assistant |
| `check_number` | READ_ONLY | No | Assistant |
| `assess_scam_risk` | READ_ONLY | No | Assistant |
| `open_protection_case` | REVERSIBLE | Yes: holds a payment and alerts the first contact | Assistant |
| `alert_trusted_contact` | REVERSIBLE | Yes, but safe to repeat | Assistant or the case owner's app |
| `get_protection_case` | READ_ONLY | No | Assistant or the case owner's app |
| `get_case_receipt` | READ_ONLY | No | Assistant or the case owner's app |
| `get_family_inbox` | READ_ONLY | No | **Family member's device only** (simulated channel) |
| `record_family_decision` | COMMITMENT | Yes: approves or rejects the payment | **Family member's device only** |

## Typical call order

```text
analyze_message  ->  check_number (optional)  ->  assess_scam_risk
      -> open_protection_case   (a HOLD also alerts the first contact)
      -> get_protection_case    (poll until the status is final)
      -> get_case_receipt

Family device:  get_family_inbox  ->  record_family_decision
```

## Tools

### `analyze_message`

Scores a message for scam warning signs. Nothing is stored.

| Argument | Type | Notes |
|---|---|---|
| `text` | string | Required. At most 2,000 characters. |
| `sender` | string, optional | A phone number. Known or suspicious numbers add a signal. |

```json
{
  "risk_score": 100,
  "risk_level": "CRITICAL",
  "signals": [
    { "name": "otp_request",   "weight": 40, "evidence": "Share your OTP" },
    { "name": "impersonation", "weight": 25, "evidence": "This is SBI" },
    { "name": "threat",        "weight": 25, "evidence": "account will be blocked" },
    { "name": "urgency",       "weight": 15, "evidence": "immediately" }
  ],
  "explanation": "This message is almost certainly a scam: it asks for an OTP, PIN or password, claims to come from a bank or an official body, threatens arrest, blocking or legal action and pushes you to act in a hurry.",
  "recommended_action": "HOLD_PAYMENTS",
  "advice": [
    "Never share an OTP, PIN, CVV or password with anyone, even if they say they are from your bank.",
    "Hang up and call the official number on your card or the bank's website.",
    "Ask a trusted family member before you reply, click or pay."
  ],
  "source": "rules",
  "model_used": false
}
```

- `source` is `"rules"` or `"rules+model"`. `model_used` says whether the Bedrock
  second opinion contributed.
- The model can only raise the score. See the design document for the scoring
  table.

### `check_number`

Looks a phone number up in the synthetic reputation list. The number is
returned masked.

| Argument | Type | Notes |
|---|---|---|
| `number` | string | Accepts `+91 90000 00001`, `09000000001`, `9000000001` and similar |

```json
{
  "found": true,
  "number_masked": "90******01",
  "reputation": "KNOWN_SCAM",
  "reports": 47
}
```

`reputation` is `KNOWN_SCAM`, `SUSPICIOUS`, `TRUSTED` or `UNKNOWN`. A number that
is not in the list, or is not a valid number, returns `found: false`,
`reputation: "UNKNOWN"` and `reports: 0`.

### `assess_scam_risk`

Decides what to do with a payment. It only evaluates the policy and does not
hold anything.

| Argument | Type | Notes |
|---|---|---|
| `owner_id` | string | The protected person, for example `user_savita` |
| `risk_score` | number | 0 to 100, normally from `analyze_message` |
| `amount` | number, optional | In rupees |
| `payee_is_new` | boolean | Default false |

```json
{
  "owner_id": "user_savita",
  "decision": "HOLD",
  "risk": "SPEND",
  "reasons": [
    "Scam risk is high (score 85) and a payment of Rs 25000 is being made.",
    "The amount is above the Rs 10000 limit and the payee is new."
  ],
  "payment_limit": 10000
}
```

`decision` is `ALLOW`, `WARN`, `HOLD` or `BLOCK`. The rules are listed in the
design document.

### `open_protection_case`

Opens a case for a payment. For a HOLD it also alerts the first trusted contact
and creates the timers, so a held payment is never left without an alert.

| Argument | Type | Notes |
|---|---|---|
| `owner_id` | string | Letters, digits, `_` and `-`, up to 64 characters |
| `risk_score` | number | 0 to 100 |
| `amount` | number | 0 to 10,000,000 |
| `payee_label` | string | Stored masked |
| `payee_is_new` | boolean | |
| `signals` | list of strings, optional | Signal names only, never message text |
| `cooling_off_minutes` | integer, optional | Clamped to 2–60. Default is the profile's 30. |

```json
{
  "task_id": "case-<uuid>",
  "kind": "scam_case",
  "owner_id": "user_savita",
  "status": "AWAITING_FAMILY",
  "risk_score": 90,
  "risk_level": "CRITICAL",
  "decision": "HOLD",
  "payment_status": "HELD",
  "payee_label": "Payee 98******10",
  "amount": 25000,
  "cooling_off_minutes": 2,
  "hold_started_at": "2026-10-18T02:15:55+00:00",
  "hold_expires_at": "2026-10-18T02:17:55+00:00",
  "alerted_contact": { "contact_id": "c_rohan", "name": "Rohan" }
}
```

(The full reply also includes `contacts`, `reasons` and other case fields.)

> **Note:** this reply is a snapshot taken before the alert completed. It can
> show `"current_contact_index": -1` and `"approvals": {}` while the status is
> already `AWAITING_FAMILY`. Call `get_protection_case` for the authoritative
> state.

For a non-HOLD decision the case is created as `CLEARED` (allow), `WARNED`
(warn) or `BLOCKED` (block) and nobody is alerted.

### `alert_trusted_contact`

Alerts the first trusted contact of a held case. It is safe to repeat: a second
call never issues a second code.

| Argument | Type |
|---|---|
| `case_id` | string |
| `owner_id` | string |

```json
{ "already_alerted": true, "status": "AWAITING_FAMILY" }
```

A first alert on a HELD case returns `case_id`, `status`, `alerted_contact`,
`hold_expires_at`, `timers_failed` and a `message`. **It never returns the
approval code.** `timers_failed` is how many timers could not be created; a
failed timer never releases money.

### `get_family_inbox`

> **Simulated delivery channel.** This stands in for an SMS or push message to
> the family member's phone. In production the message would arrive out of
> band, never through MCP. It is not for use by the assistant.

| Argument | Type |
|---|---|
| `case_id` | string |
| `contact_id` | string, for example `c_rohan` |

```json
{
  "found": true,
  "for": "Rohan",
  "message": "Payment of Rs 25000 to Payee 98******10 is on hold. Approve or reject.",
  "approval_code": "ABCD2345"
}
```

Returns `{ "found": false }` when the case is not waiting for a decision, when
that contact was never alerted, or after the entry is used or expired. This is
the only tool whose reply contains the approval code.

### `record_family_decision`

Records a family member's decision. Only the family member's device may call
this, with the approval code. An assistant must never call it on its own.

| Argument | Type | Notes |
|---|---|---|
| `case_id` | string | |
| `contact_id` | string | |
| `approval_code` | string | Spaces, dashes and lowercase are accepted |
| `decision` | string | Exactly `APPROVE` or `REJECT` |

Approved:

```json
{
  "case_id": "case-<uuid>",
  "status": "APPROVED",
  "payment_status": "RELEASED",
  "decided_by": "c_rohan",
  "message": "Payment approved and released."
}
```

Wrong code:

```json
{ "error": "Invalid approval code", "attempts_left": 2 }
```

A rejection returns `status: "REJECTED"` and `payment_status: "BLOCKED"`. The
first valid decision wins; any later decision returns
`{ "error": "Case already decided" }`.

### `get_protection_case`

Reads the current state of a case.

| Argument | Type |
|---|---|
| `case_id` | string |
| `owner_id` | string |

Returns the case record (see the data model in the design document). The
`approvals` map shows `issued_at`, `expires_at`, `used` and `attempts` for each
alerted contact, and never a code. A wrong `owner_id` gets exactly the same
reply as a missing case:

```json
{ "error": "Case not found" }
```

### `get_case_receipt`

Returns the evidence trail, safe to attach to a complaint.

| Argument | Type |
|---|---|
| `case_id` | string |
| `owner_id` | string |

The reply has these top-level keys: `version`, `event_count`, `events`,
`answers`, `case` and `complaint_summary`.

```json
{
  "events": [
    {
      "event_type": "CASE_OPENED",
      "timestamp": "2026-10-18T02:15:55+00:00",
      "summary": "Protection case opened with risk 90 (CRITICAL).",
      "details": { "status": "HELD", "risk_score": 90, "payee_label": "Payee 98******10" }
    },
    {
      "event_type": "PAYMENT_HELD",
      "summary": "Rs 25000 to Payee 98******10 was put on hold."
    }
  ],
  "answers": {
    "why_it_was_flagged": ["otp_request", "impersonation"],
    "what_was_held": "Rs 25000 to Payee 98******10 (payment status: BLOCKED).",
    "who_decided_and_how": "nobody answered",
    "final_outcome": "Nobody answered before the hold expired. The payment stayed blocked."
  },
  "complaint_summary": "Relay Shield case case-<uuid>\nOpened (UTC): …\nPayment: Rs 25000 to Payee 98******10 (masked payee).\nOutcome: Nobody answered before the hold expired. The payment stayed blocked."
}
```

Approval codes and any key named `approval_code`, `token` or `secret` are never
included, at any depth.

## Resource and prompt

| Item | Name | What it gives |
|---|---|---|
| Resource | `relay://shield/profile/{owner_id}` | The protected person's payment limit and trusted contacts (no phone details) |
| Prompt | `protect_family_from_scam` (arguments `owner_id`, `message`) | A workflow for an assistant: analyze, check numbers, assess a payment, open a case on HOLD, explain calmly. It forbids approving, asking for codes, and giving legal or financial advice. |

## Error messages

| Message | Meaning |
|---|---|
| `Case not found` | The case does not exist, **or belongs to another owner** (deliberately the same answer) |
| `Unknown protected user` | No profile for that `owner_id` |
| `Invalid owner_id` | Not letters, digits, `_` or `-`, or longer than 64 characters |
| `Amount must be between 0 and 10000000` | Amount out of range |
| `Message text must be a string` | `analyze_message` got something other than text |
| `Message text must be 2000 characters or fewer` | Message too long |
| `Case cannot be alerted while <STATUS>` | Alerting is only allowed while HELD or AWAITING_FAMILY |
| `Too many alert calls for this case` | More than 5 alert calls |
| `Case changed while alerting` | Another change won a race; read the case and retry |
| `No trusted contact is configured` | The profile has no contacts |
| `Decision must be APPROVE or REJECT` | Exact upper-case words are required |
| `No active approval for this contact` | That contact was not alerted, or its entry is used or expired |
| `Invalid approval code` | Wrong code; `attempts_left` says how many tries remain |
| `Too many wrong codes. This contact is locked.` | Three wrong codes for this contact |
| `Case already decided` | Someone already approved or rejected, or the hold ended |
| `RELAY_SHIELD_SECRET is not set` | Server misconfiguration; alerting and deciding fail closed |

## Limits

| Limit | Value |
|---|---|
| Message length for `analyze_message` | 2,000 characters |
| Characters scanned by the rules engine | 20,000 |
| Characters sent to the Bedrock model | 1,500 |
| Bedrock timeout | 8 seconds |
| Payment amount | 0 to 10,000,000 |
| Cooling-off period | 2 to 60 minutes |
| Wrong codes per contact | 3, then locked |
| Alert calls per case | 5 |
| `owner_id` | letters, digits, `_`, `-`; 1 to 64 characters |

## Which tools an assistant may use

The optional Bedrock agent layer (`relay/agent_tools.py`) exposes only six of the
original errand tools (create and get an errand, find, propose and select
providers, and read the audit log). It exposes **none** of the Relay Shield
tools, and a test checks that `alert_trusted_contact`,
`record_family_decision` and `get_family_inbox` are never added to it.

Other MCP clients, such as Alexa+, see all 26 tools. For them the protection is
the tool descriptions, the `protect_family_from_scam` prompt (which forbids
approving payments or reading family codes), and the one-time approval code.
That is procedural in this prototype; see
[relay-shield-security.md](./relay-shield-security.md) for what production
would change.
