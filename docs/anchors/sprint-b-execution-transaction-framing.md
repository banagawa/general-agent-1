# Sprint B — Execution Transaction Framing (Complete)

Status: Complete (merged to main)
Classification: Enforcement Extension (No New Subsystems)

Branch: sprint-b-impl  
Merge Commit: <fill after merge>  
Date Closed: 2026-03-03

This sprint introduces execution-phase transaction framing within ToolGateway.

It does not introduce filesystem snapshotting, restore engines, background workers, or new mutation systems.

---

## Historical Context

Sprint History lists:

> Sprint B — Transactional Execution Engine :contentReference[oaicite:0]{index=0}

Initial concept implied workspace-level rollback.  
After strategic review, scope was narrowed to execution framing only.

This preserves simplicity and avoids subsystem expansion.

---

## Objective

Strengthen fail-closed behavior and audit clarity for execution-phase mutation tools.

Goals:

- Deterministic execution envelope
- Explicit transaction lifecycle events
- Failure-class classification
- No authority expansion

---

## Architectural Alignment

This sprint must preserve:

Core Spine:
Orchestrator → AgentLoop → ToolGateway → PolicyEngine → Tool :contentReference[oaicite:1]{index=1}

Security Guarantees:
- Deny-by-default
- Workspace boundary invariant
- Patch-only mutation
- Append-only audit
- Fail-closed enforcement :contentReference[oaicite:2]{index=2}

No invariant may be weakened.

---

## Scope

Applies to:

- Execution-phase mutation tools (e.g., CMD_RUN)
- Multi-step execution flows within a single loop cycle

Does NOT apply to:

- Patch proposal lifecycle
- Patch approval lifecycle
- Revocation model
- Capability tokens
- Workspace boundary logic

---

## Transaction Model

Transaction is a logical execution wrapper.

Lifecycle:

1. TRANSACTION_START
2. Tool execution
3. Either:
   - TRANSACTION_COMMIT
   - TRANSACTION_ROLLBACK

Rollback means:
- Abort execution
- Emit audit event
- Return control

No filesystem snapshot or restore is introduced.

---

## Rollback Triggers

Rollback occurs on:

- Policy denial
- Tool execution error
- Timeout
- Unexpected exception
- Explicit abort

System must deny and log before returning control.

---

## Audit Events (Additive Only)

New events:

- TRANSACTION_START
- TRANSACTION_COMMIT
- TRANSACTION_ROLLBACK

Schema must remain backward compatible.

Existing audit events must not be modified.

---

## Implementation Constraints

Transaction framing must:

- Live inside ToolGateway
- Not bypass PolicyEngine
- Not introduce new persistence layers
- Not introduce background execution
- Not introduce parallel mutation control
- Not introduce privilege expansion

If implementation requires a new subsystem, scope must be reconsidered.

---

## Definition of Done

- Execution-phase mutation tools run inside transaction wrapper.
- Failures are classified and audited.
- No regression in Sprint A or A5.
- No invariant violations.
- No authority expansion.

---

## Governance Note

This sprint is an enforcement extension, not a platform expansion.

Any refactor that introduces snapshot engines, restore layers, background agents, or dual mutation systems violates this document.
