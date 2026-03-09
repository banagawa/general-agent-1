# Sprint History

## Sprint A — Sandbox & ToolGateway

Goal:
Create sandbox environment and enforce all tool access through ToolGateway.

Features:
- sandbox execution
- workspace boundary
- basic policy enforcement

Status: Complete

---

## Sprint B — Capability Enforcement

Goal:
Introduce capability tokens for tool execution.

Features:
- token issuance
- token validation
- deny-by-default policy

Status: Complete

---

## Sprint C — Repo Kernel

Goal:
Create deterministic repo-level execution kernel.

Features:
- patch-based file modification
- structured tool calls
- execution audit events

Status: Complete

---

## Sprint D — Structured Plan Artifact

Branch: sprint-d-structured-plan-artifact
Status: Complete
Closed: 2026-03-07

Goal:
Introduce deterministic PLAN artifact and approval gate.

Outcome:
- deterministic plan schema
- explicit approval gate
- execution only via approved plans
- plan hash recorded in audit
- raw execution commands blocked
  
Features:
- deterministic plan schema
- plan validation
- plan approval gate
- plan hash recorded in audit
- execution only via approved plans
- automatic capability token issuance during execution

Commands:
plan.submit
plan.approve
plan.execute

Execution model:
plan.submit → validate_plan → store_pending_plan
plan.approve → mark_plan_approved
plan.execute → execute_plan

---

## Sprint E — Deterministic Dev Loop

Branch: sprint-e-deterministic-dev-loop
Status: In Progress

Goal:
Close a small development cycle deterministically and safely:

PLAN → EXECUTE → TEST → DIFF → SUMMARIZE

Planned features:
- automatic test execution
- failure capture and classification
- transaction-scoped execution
- replay prevention
- deterministic summary output
