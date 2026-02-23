# Architecture Contract

This document defines the non-negotiable architectural invariants of the General Agent system.

If conversation context or future refactors conflict with this document, this document wins.

---

## Core Enforcement Spine

All tool access must flow through:

Orchestrator → AgentLoop → ToolGateway → PolicyEngine → Tool Implementation

No tool may be invoked directly from the loop or orchestrator.

---

## Security Model

### 1. Deny-By-Default

- All actions are denied unless explicitly allowed.
- PolicyEngine.is_allowed() is the single enforcement gate.

### 2. Workspace Boundary

- All file system operations must be contained within WORKSPACE_ROOT.
- All paths must be canonicalized using resolve().
- relative_to() or equivalent boundary enforcement must be used.
- Any path outside WORKSPACE_ROOT must fail closed.

### 3. No Shell Passthrough

- subprocess must always use shell=False.
- Commands must be passed as argv lists only.
- Single-string commands are forbidden.

### 4. Patch-Only Writes

- No direct full-file overwrites.
- All writes must be patch-based (diff-visible).
- No silent mutation.

### 5. Explicit Approval

- Write operations require proposal + approval flow.
- Revocation must block both propose and approve.
- Revocation must persist across CLI runs.

### 6. Audit Everything

- All tool calls must generate audit events.
- Both allow and deny events must be logged.
- Audit must be append-only.
- Failures must also be logged.

### 7. Fail-Closed Design

If anything unexpected occurs:
- Deny.
- Log.
- Do not partially execute.

---

## Explicit Non-Goals (Current Phase)

- No autonomy.
- No background execution.
- No network connectors.
- No self-escalating permissions.
