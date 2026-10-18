# Production Alexa+ Authentication Path

Relay's current hackathon deployment demonstrates a real remote MCP server plus host/origin validation.

A production Alexa+ Add-on would additionally require OAuth 2.1 account linking.

## Target Architecture

```text
Alexa+
  |
  | Authorization Code Flow + PKCE (S256)
  v
Authorization Server
  |
  | access token
  v
Alexa+
  |
  | Authorization: Bearer <token>
  v
Relay MCP
  |
  | user_id / scopes / task ownership
  v
Per-user Relay authorization
  |
  +--> RelayTasks
  +--> RelayAudit
```

## Production Requirements

1. Return `401 Unauthorized` for unauthenticated MCP requests.
2. Publish Protected Resource Metadata at the standard well-known URI.
3. Publish authorization-server metadata.
4. Use OAuth authorization-code flow.
5. Use PKCE with `S256`.
6. Set Relay's canonical MCP URI as the OAuth `resource`.
7. Send Bearer tokens in the `Authorization` header.
8. Enforce per-user task ownership.
9. Enforce per-tool scopes.
10. Never send bearer tokens in query parameters.

## Suggested Relay Scopes

```text
relay.tasks.read
relay.tasks.write
relay.tasks.approve
relay.tasks.schedule
relay.audit.read
```

## Example Authorization Policy

```text
create_errand
    requires relay.tasks.write

get_errand
    requires relay.tasks.read
    and task belongs to caller

find_providers
    requires relay.tasks.read

select_provider
    requires relay.tasks.write

approve_booking
    requires relay.tasks.approve
    and task belongs to caller

schedule_task_resume
    requires relay.tasks.schedule

get_audit_log
    requires relay.audit.read
    and task belongs to caller
```

## Why This Is Documented Rather Than Claimed As Complete

The current project is a hackathon prototype using a simulated Alexa+ client surface.

The MCP backend, durable state, failure recovery, scheduling, resume path, policy enforcement, and audit trail are real.

Production OAuth/account linking is documented as the next deployment boundary rather than represented as already implemented.


## Relay Shield Security Boundary

Relay Shield currently uses a simulated family-phone delivery channel for the
hackathon demonstration. `get_family_inbox` represents the SMS or push channel
that a production service would use. The approval code is exposed only through
that simulated family channel and must never be returned by general assistant
tools, receipts, audit events, or logs.

The current prototype also receives `owner_id` as a tool argument. Production
deployment must derive the protected user's identity from an authenticated
identity provider rather than trusting a model-supplied identifier. Amazon
Cognito or another OAuth/OIDC identity provider could supply the verified
subject used for task ownership checks.

`RELAY_SHIELD_SECRET` is required by the server and has no application default.
Production deployment should store it in a managed secrets system and inject it
into the ECS task as a secret. The Bedrock/OpenAI-compatible API credential
(`OPENAI_API_KEY`) must likewise remain outside the repository and be injected
as an ECS secret.

Production family approval delivery would use SMS or push notifications tied to
a verified trusted-contact identity. The MCP assistant must never receive the
approval code and must never make the family decision itself.

Relay Shield applies default-deny behavior: invalid input is refused, unknown
ownership is indistinguishable from a missing case, approval codes lock after
repeated failures, payment amounts are bounded, owner identifiers are
restricted to a safe format, and silence never releases a held payment.

For the full Relay Shield threat table and what is simulated, see
[relay-shield-security.md](./relay-shield-security.md).
