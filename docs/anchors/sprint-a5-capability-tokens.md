# Sprint A5 — Capability Tokens (Complete)

This sprint adds capability tokens as a fail-closed authorization layer enforced at the ToolGateway.

---

## Status
**Complete (pending merge to main)**

## Branch
`/sprint-a5-capability-tokens`

## Commits
- `02ddee6` — Sprint A5: capability tokens enforced at ToolGateway (fail-closed)
- `cdcd8c6` — Sprint A5: make audit schema backward-compatible (event/meta + action/.../detail)

## Goal
Add capability tokens to enforce fine-grained, revocable, time-bounded permissioning while preserving the existing deny-by-default + audit-first architecture.

## Implemented Capabilities
### Capability Tokens
- ToolGateway requires a valid capability token for protected operations.
- Token validation is **fail-closed** (missing/invalid token => deny + audit).
- Token model supports expiry semantics (as implemented in this sprint).

### Revocation / Deny Semantics
- Tokens can be revoked (as implemented) and revocation is enforced before any tool executes.
- Deny outcomes are always audited.

### Audit Schema Compatibility
- Audit output remains backward-compatible for existing consumers by supporting both:
  - legacy-ish fields (action/detail)
  - newer structured grouping (event/meta)

## Security Guarantees Preserved
- Orchestrator → AgentLoop → ToolGateway → PolicyEngine → Tool remains the only execution path.
- Deny-by-default remains the default posture.
- Audit remains mandatory for allow + deny.

## Test Notes
- Ensure unit tests cover: missing token, invalid token, expired token, revoked token, and allowed token.
- Ensure audit log events are emitted for each deny case.

## Merge Record (fill on merge)
- Merge commit: 082c013
- Date: 2026-2-25
