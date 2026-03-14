# security-invariants.md

Status: Architecture Anchor

Purpose:
Define permanent control invariants that protect the system from drift.

If any sprint doc or roadmap conflicts with this file, this file wins.

---

## Core Principle

Capability may expand.
Control invariants may not weaken.

---

## Non Negotiable Invariants

1. ToolGateway remains execution choke point.

2. Deny-by-default policy.

3. Workspace boundary enforcement.

4. Patch-only mutation model.

5. Explicit approval for mutation.

6. Append-only audit logging.

7. Fail-closed error handling.

---

## Execution Model

Execution must follow:

plan.submit → plan.approve → plan.execute → execute_step → ToolGateway

No alternate execution path may exist.