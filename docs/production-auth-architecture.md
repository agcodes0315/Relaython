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
