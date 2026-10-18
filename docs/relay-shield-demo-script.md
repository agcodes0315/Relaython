# Relay Shield — Demo Script

A script for the demo video. **Target length: 2:45. Devpost's limit is 3:00.**
The video must be public on YouTube or Vimeo, in English, with no copyrighted
music and no third-party trademarks on screen.

> The sample message in the UI mentions an electricity board. Keep it generic:
> do not show a real bank's or company's logo.

- [Before you record](#before-you-record)
- [The script](#the-script)
- [What to say if something goes wrong](#what-to-say-if-something-goes-wrong)
- [Lines to remember](#lines-to-remember)

## Before you record

| Check | How |
|---|---|
| The server is the new one (26 tools) | `curl -s $BASE/health` shows `"scam_shield":true` |
| The real endpoint answers, not only `/health` | The 200 and 421 checks in [relay-shield-operations.md](./relay-shield-operations.md#5-after-every-deployment) |
| `RELAY_SHIELD_SECRET` is set | Otherwise the alert fails closed with `RELAY_SHIELD_SECRET is not set` |
| The UI talks to the server you mean | `MCP_URL` in `relay-ui/server/bridge.mjs` |
| The bridge and UI are running | `node server/bridge.mjs`, then `npm run dev` in `relay-ui/` |
| A short hold for the demo | Nothing to set: the UI opens every case with a 2-minute hold, so escalation (about 1 minute) and expiry (about 2 minutes) fit in a recording |
| One dry run | Run the whole script once and delete the cases it made |
| Browser tidy | One tab, zoom 110–125%, no bookmarks bar, no notifications |

Two windows are easiest: **Savita's phone** (the protected person's side) and
the **family phone** (the right-hand panel in the UI).

## The script

| Time | On screen | Say |
|---|---|---|
| 0:00–0:15 | The Relay Shield view, Savita's phone with the sample message | "Scams don't break security. They pressure people. Savita gets a message that says her power will be cut today unless she pays 25,000 rupees now." |
| 0:15–0:35 | Click **Analyze message**. Show the score, the level and the signals | "Relay Shield scores it with transparent rules: urgency, a threat, a payment demand. Each signal shows the evidence, with numbers masked. An optional Bedrock model can add a second opinion, but it can only raise the score, never lower it." |
| 0:35–0:55 | Set the amount to 25,000 and click **Assess ₹25,000 payment**. Show the HOLD | "Now Savita tries to pay. Policy, not a model, decides: high risk plus a payment means HOLD. The money is held and the case is opened." |
| 0:55–1:20 | The audit trail with the case opened and the family alert. Point at the alert to Rohan | "A durable case is stored in DynamoDB. Rohan is alerted. Notice what the assistant did **not** receive: the approval code. The assistant cannot approve its own payment." |
| 1:20–1:50 | Switch to **Rohan's** panel. Show the message and the one-time code, then click **Reject** | "This panel is the family member's phone. It is simulated here, and in production it is an SMS or push message. Only a valid one-time code works, and three wrong codes lock the contact. Rohan checks with Savita and rejects. The payment is blocked." |
| 1:50–2:10 | Show the status REJECTED and the payment BLOCKED. Click **Copy complaint evidence** | "Every step is in the receipt: why it was flagged, what was held, who decided, and the outcome. One click gives Savita evidence for her bank." |
| 2:10–2:35 | A second case, already run beforehand and cut in. Show the timeline: alert, escalation to Anita, expiry, EXPIRED_BLOCKED | "And when nobody answers? EventBridge wakes a Lambda that moves to the next contact, and finally blocks the payment. **Silence never releases money.**" |
| 2:35–2:45 | The AWS console: ECS, DynamoDB, EventBridge schedules, Lambda | "ECS, DynamoDB, EventBridge Scheduler, Lambda and Bedrock, exposed as 26 MCP tools for Alexa+. Reasoning may be probabilistic. Authority should not be." |

### Tips for the expiry clip

Record it on its own the day before. Open a case (the UI uses a 2-minute hold), answer
with nothing, and capture the timeline as Anita is alerted at about 1 minute and
the case expires at about 2 minutes. Cut it down to 25 seconds. Say in the
video or the description that it was sped up if you speed it up.

## What to say if something goes wrong

| Problem | Do this |
|---|---|
| The UI shows an error | Check `MCP_URL` and that the bridge is running. Do not retry live in the video: stop and fix it, then record again |
| The Bedrock reply is slow or fails | The rules still work: the result says `"source": "rules"`. Say so; it is a feature |
| `Too many wrong codes` | The contact is locked, which is the behavior. Open a new case |
| The case says `AWAITING_FAMILY` after the first alert | The reply from `open_protection_case` is a snapshot taken before the alert. Read the case again |

## Lines to remember

- **Silence never releases money.**
- **Reasoning may be probabilistic. Authority should not be.**
- The assistant can analyze and explain. Only a human with a one-time code can
  release a payment.
- The family phone is simulated. The backend, timers, state machine and audit
  trail are real.

## Honest framing for the judges

Say this plainly, in the video or in the description: the family phone and the
user's identity are simulated in this prototype, and the production plan is in
[production-auth-architecture.md](./production-auth-architecture.md). Judges
trust a team that names its limits.
