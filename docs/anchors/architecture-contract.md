# Architecture Contract

Status: Anchor

This file describes the core execution contract that merged runtime behavior must preserve.

If another document conflicts with this file, this file wins.

---

## Sprint F Autonomy Contract

Controlled autonomy does not change the execution spine.

`task.autonomy` may create a pending plan through the same TaskSpec/planner/submit path as `task.plan`.

Autonomy modes:
- `MANUAL`
- `ASSISTED`
- `BOUNDED_AUTONOMOUS`

Required constraints:
- bounded autonomy is disabled unless `AGENT_BOUNDED_AUTONOMY_ENABLED` is enabled
- all autonomy modes stop at pending approval
- only `plan.execute` may execute steps
- runtime, cycle, and mutation budgets must fail closed before submit
- mutation failures must trigger rollback
- rollback must restore earliest-original-state per path
- decision points must be audited

No autonomy mode may invoke tools directly.

---

## Core Spine

All execution must follow:

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

### 4. Typed patch-only mutation
- no silent direct overwrite path
- mutation must remain diff-visible
- mutation must stay scoped to approved tool behavior
- `PATCH_APPLY` and `PATCH_EDIT` remain separate typed operations

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

## Typed Mutation Contract

### PATCH_APPLY
- whole-file replacement only
- target file must already exist
- exact-path scoped token
- audited

### PATCH_EDIT
- anchored exact-text replacement only
- target file must already exist
- exact `old_text` to exact `new_text`
- optional 1-based `occurrence`
- optional `expected_file_sha256_before`
- exact-path scoped token
- audited

`PATCH_EDIT` must not become:
- regex editing
- fuzzy matching
- AST patching
- line-number-only targeting
- silent fallback to whole-file rewrite

Multi-edit PATCH_EDIT is atomic:
- edits apply in declared order to in-memory content
- any failed edit denies the whole step
- nothing is written on failure

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
