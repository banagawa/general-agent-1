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
Status: Complete
closed:2026-03-12

Goal: Close a full development cycle automatically.

Deliver:

- Plan → Execute → Test → Diff → Summarize execution loop
- Deterministic step execution through ToolGateway
- Transaction-scoped execution context
- Execution summaries written to `plans/summaries`
- Replay protection via executed markers
- Failure envelopes written to `plans/failures`
- Mutation cap enforcement
- Step cap enforcement
- Transaction time budget enforcement

Artifacts:

plans/approved/<plan_hash>.json  
plans/executed/<plan_hash>.json  
plans/summaries/<plan_hash>-<tx_id>.json  
plans/failures/<plan_hash>-<tx_id>.json  

Execution Path:

Orchestrator  
→ AgentLoop  
→ execute_plan  
→ execute_step  
→ ToolGateway  
→ PolicyEngine  
→ Tool Implementation  

Outcome:
Agent can complete small development cycles deterministically.
