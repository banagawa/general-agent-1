# Sprint History

## Sprint A — Sandbox & ToolGateway

Goal:
Create the sandbox environment and force all tool access through ToolGateway.

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
Create a deterministic repo-level execution kernel.

Features:
- patch-based file modification
- structured tool calls
- execution audit events

Status: Complete

---

## Sprint D — Structured Plan Artifact

Branch: `sprint-d-structured-plan-artifact`
Status: Complete
Closed: 2026-03-07

Goal:
Introduce a deterministic PLAN artifact and approval gate.

Outcome:
- deterministic plan schema
- explicit approval gate
- execution only via approved plans
- plan hash recorded in audit
- raw execution commands blocked

Features:
- deterministic plan schema
- plan validation
- pending and approved plan storage
- plan approval gate
- plan hash recorded in audit
- automatic capability token issuance during execution

Command surface:
- `plan.submit`
- `plan.approve`
- `plan.execute`

Execution model:
`plan.submit` → validate_plan → store_pending_plan  
`plan.approve` → mark_plan_approved  
`plan.execute` → execute_plan

---

## Sprint E — Deterministic Dev Loop + Planner Front Door

Branch lineage:
- `sprint-e-deterministic-dev-loop`
- `sprint-e-llm-integration-plan`

Status: Complete on `main`
Closed: 2026-03-17

Goal:
Close a small development cycle deterministically without weakening the security model.

Delivered in Sprint E:

### Execution layer
- approved-plan-only execution
- deterministic step execution through ToolGateway
- transaction-scoped execution records
- execution summaries written to `plans/summaries`
- failure envelopes written to `plans/failures`
- replay denial via executed markers
- step cap enforcement
- execution time budget enforcement

### Approval hardening
- workspace fingerprint captured at approval time
- execution denied when workspace drift is detected before run
- approval metadata written to `plans/approved/<plan_hash>.meta.json`

### Planner layer
- `task.plan` command surface added
- raw task normalized into `TaskSpec`
- deterministic planner path retained
- optional LLM planner path added behind planner controls
- planner output validated, then stored as a pending plan
- planner remains proposal-only and cannot bypass approval or ToolGateway

Artifacts:
- `plans/pending/<plan_hash>.json`
- `plans/approved/<plan_hash>.json`
- `plans/approved/<plan_hash>.meta.json`
- `plans/executed/<plan_hash>.json`
- `plans/summaries/<plan_hash>-<tx_id>.json`
- `plans/failures/<plan_hash>-<tx_id>.json`

Execution path:
Human  
→ `task.plan` or `plan.submit`  
→ `plan.approve`  
→ `plan.execute`  
→ Orchestrator  
→ AgentLoop  
→ PlanExecutor  
→ execute_step  
→ ToolGateway  
→ PolicyEngine  
→ Tool Implementation

Audit additions in this sprint:
- `PLAN_SUMMARY_RECORDED`
- `PLAN_FAILURE_ENVELOPE_RECORDED`
- `PLAN_EXECUTION_REPLAY_DENIED`
- `PLAN_EXECUTION_DRIFT_DENIED`
- `PLANNER_REQUESTED`
- `PLANNER_PLAN_CREATED`
- `PLANNER_DENIED`

Outcome:
The agent can now take a user task, turn it into a controlled plan, require explicit approval, and execute that plan deterministically with replay denial, drift checks, summaries, and failure envelopes.

Post-closeout hardening completed after Sprint E added:

- central preflight execution validation
- explicit execution state transitions
- centralized deny reasons and audit payloads
- stricter ingress validation
- concurrent replay coverage
- audit reason-code verification
- documented crash semantics for `IN_FLIGHT`

This did not create a new sprint.
It hardened the merged Sprint E execution control plane and clarified the system state that shipped after Sprint E completion.
