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

## Explicitly NOT Implemented

- Capability tokens
- Token expiry enforcement
- UX layer
- Connectors
- Autonomy
- Network calls
- Background agents

---

## Tool Inventory

FS_READ  
FS_SEARCH  
FS_WRITE_PATCH  
CMD_RUN

---

## Security Guarantees

- Deny-before-allow policy
- Workspace boundary invariant
- Patch-only mutation
- Fail-closed enforcement
- Auditable lifecycle
