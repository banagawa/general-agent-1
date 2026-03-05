# System State v1

This document defines the current canonical system state as of:

Commit: dbf73b362e0ee8f7a2334387242b319c3151063a
Branch: main  

---

## Implemented Capabilities

### Workspace Enforcement
- WORKSPACE_ROOT configurable via environment variable.
- All file operations constrained under workspace.
- Canonical path enforcement.

### Deny Patterns
- `.env`
- `secrets`
- `credentials`

### Read-Only Spine
- File search (filtered extensions)
- File read with size cap
- Policy-filtered search results
- Persistent audit logging (.audit/audit.jsonl)

### Patch-Based Write System
- Propose patch → returns ID + diff
- Approve patch → applies mutation
- Revocation persists across runs
- Revocation blocks propose + approve
- Pending patches stored on disk
- Full audit trail for lifecycle

---

## Sprint A (Merged)

CMD_RUN:

- Allowlisted commands only
- No shell passthrough
- Forced cwd to WORKSPACE_ROOT
- Timeout enforcement
- Output truncation
- Structured return object
- Audit allow + deny events

--- 
## Sprint A5 (Merged)
Capability Tokens:
- Capability token enforcement at ToolGateway (fail-closed)
- Token expiry enforcement
- Token revocation enforcement
Audit:
- Backward-compatible audit schema (event/meta + action/.../detail)

---

## Sprint B (Merged)

Execution Transaction Framing:

- Logical transaction wrapper inside ToolGateway
- TRANSACTION_START / TRANSACTION_COMMIT / TRANSACTION_ROLLBACK events
- Deterministic tx_id correlation
- duration_ms recorded for commit/rollback
- Rollback on:
  - Policy denial
  - Capability denial
  - Timeout
  - Unexpected exception

Security Guarantees Preserved:
- ToolGateway remains enforcement choke point
- No new subsystems introduced
- No filesystem snapshot/restore
- Fail-closed behavior preserved
- Audit remains append-only
---

### Sprint C — Repo Kernel (Complete)

Scope:
- Introduce GIT_RUN tool behind ToolGateway
- Strict subcommand allowlist: init, status, diff, add, commit, log
- Deny unknown flags and git config overrides
- No remote/branch/network operations
- Token-gated mutating commands
- Full audit coverage (allow + deny)
- Workspace boundary enforced

Status: Complete

---

### Sprint D — Structured Plan Artifact (Planned)

Scope:
- Deterministic PLAN schema
- Ordered tool steps with parsed arguments
- Capability scope per step
- No execution until plan approval
- Plan hash logged in audit
- Fail closed on schema violation

Status: In progress

---

## Explicitly NOT Implemented

- UX layer
- Connectors
- Autonomy
- Network calls
- Background agents

---

## Tool Inventory

- FS_READ
- FS_WRITE (token-gated)
- FS_SEARCH
- CMD_RUN (token-gated)
- GIT_RUN (token-gated for mutations)

---

## Security Guarantees

- Deny-before-allow policy
- Workspace boundary invariant
- Patch-only mutation
- Fail-closed enforcement
- Auditable lifecycle
