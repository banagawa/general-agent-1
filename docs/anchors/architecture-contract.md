# Architecture Contract

This document defines the non-negotiable architectural invariants of the General Agent system.

If future refactors, planner integrations, or convenience features conflict with this document, this document wins.

---

## Core Enforcement Spine

All tool access must flow through:

Orchestrator → AgentLoop → PlanExecutor → execute_step → ToolGateway → PolicyEngine → Tool Implementation

Planner entry does not change that spine.

`task.plan` may create a pending plan.  
`plan.submit` may create a pending plan.  
Only `plan.execute` may run steps.  
All step execution must still pass through ToolGateway.

No tool may be invoked directly from the loop, planner, or orchestrator.

---

## Security Model

### 1. Deny-by-default

- all actions are denied unless explicitly allowed
- `PolicyEngine.is_allowed()` is the execution gate
- unexpected states fail closed

### 2. Workspace boundary

- all file operations must remain within `WORKSPACE_ROOT`
- paths must be canonicalized with `resolve()`
- boundary enforcement must use `relative_to()` or equivalent
- escape attempts must fail closed

### 3. No shell passthrough

- subprocess execution must use `shell=False`
- commands must be passed as argv lists only
- single-string shell commands are forbidden

### 4. Patch-only writes

- no silent direct overwrite path
- file mutation must remain diff-visible
- mutation must stay scoped to approved tool behavior

### 5. Explicit approval before execution

- mutation-capable execution requires a plan artifact
- the plan must be approved before execution
- raw execution commands remain blocked
- planner-generated plans are not self-approving

### 6. Approval binds to workspace state

- approval records a `workspace_fingerprint`
- execution verifies the current workspace fingerprint before the run starts
- fingerprint mismatch must deny execution
- drift denial must require a new approval cycle

### 7. Capability-scoped execution

- each executable step receives a short-lived scoped token
- token scope must match the tool and step being executed
- capability checks must remain fail-closed

### 8. Audit everything

- all major lifecycle actions must emit audit events
- allow and deny paths must both be logged
- summary and failure recording must be logged
- audit remains append-only

### 9. Fail-closed design

If anything unexpected occurs:
- deny
- log
- do not partially bypass controls

---

## Planner Boundary

Planner assistance is allowed only as proposal generation.

Planner may:
- normalize a human task into `TaskSpec`
- generate plan JSON
- attach planner and intent metadata

Planner may not:
- execute tools
- approve plans
- bypass ToolGateway
- bypass PolicyEngine
- mutate files outside approved execution

This holds for both deterministic and LLM-backed planner paths.

---

## Current Execution Lifecycle

Plan creation:
- `task.plan` → planner output → validated pending plan
- `plan.submit` → validated pending plan

Approval:
- `plan.approve` → approved plan + approval metadata

Execution:
- `plan.execute` → deterministic execution loop

Execution artifacts:
- `plans/approved/<plan_hash>.json`
- `plans/approved/<plan_hash>.meta.json`
- `plans/executed/<plan_hash>.json`
- `plans/summaries/<plan_hash>-<tx_id>.json`
- `plans/failures/<plan_hash>-<tx_id>.json`

Execution denials include at least:
- plan not approved
- replay attempt on an already executed plan
- workspace drift detected
- step cap exceeded
- time budget exceeded

---

## Explicit Non-Goals in Current Merged State

- no uncontrolled autonomy
- no background execution
- no network connector execution path in the runtime loop
- no self-escalating permissions
- no planner-driven approval bypass

---

## Sprint E Contract Update

Sprint E is complete and extends the contract in two ways without weakening it:

1. deterministic execution artifacts are now first-class
2. planner-assisted plan creation exists through `task.plan`

The security boundary is unchanged:
planning may propose  
approval must authorize  
execution must remain ToolGateway-mediated
