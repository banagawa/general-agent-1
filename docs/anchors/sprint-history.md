# Sprint History

## Current merged-state ledger through Sprint H Slice 7

This section reconciles the repository history with merged PRs and commits.

| Area | PRs | Merge commits | Status |
|---|---|---|---|
| Worktree root hardening before Sprint G closeout | #10-#11 | `da5d860`, `7f6f552` | Complete |
| Sprint G deterministic improvement engine | #12 | `e5e0327` | Complete |
| Pre-Sprint-H hardening | #13-#22 | `52c05fb` through `49eabfc` | Complete |
| Sprint H workspace intelligence | #23-#29 | `e396a53` through `f79a6e0` | Complete through Slice 7 |

Detailed current-state ledger: `docs/anchors/current-state-ledger-v6.md`.

Pre-Sprint-H hardening closeout: `docs/sprints/pre-sprint-h-hardening-closeout-v6.md`.

Sprint H closeout: `docs/sprints/sprint-h-closeout-v6.md`.

---

## Sprint G — Deterministic Improvement Engine Foundation

Branch: `sprint-g-deterministic-improvement-engine`
Status: Complete

Goal:
Allow the agent to improve development strategy across cycles using deterministic execution outcomes while preserving approval gates, deny-by-default policy, workspace isolation, and append-only auditability.

Outcome:
- `CycleOutcome` centralizes execution outcome vocabulary
- inert strategy and strategy proposal data models added
- append-only strategy registry added
- deterministic strategy proposal engine added
- post-cycle proposal hook added after execution summary/failure-envelope creation
- strategy proposals do not auto-install
- no policy, tool-surface, autonomy, or strategy-driven schema expansion
- `TEST_RUN` cwd selection supports app-root and workspace-root testing

Security boundary:
- strategies are data only
- registry is append-only
- proposal generation is inert and auditable
- human approval remains required for any future strategy installation
- app/workspace/test roots remain explicitly separated

---

## Sprint F — Controlled Autonomy Mode

Branch: `agent-self-dev`
Status: Complete
Closed: 2026-05-18

Goal:
Reduce operational involvement while preserving PLAN approval, capability scope, workspace boundary, rollback safety, and auditability.

Outcome:
- `task.autonomy` command added
- `MANUAL`, `ASSISTED`, and `BOUNDED_AUTONOMOUS` modes implemented
- bounded autonomy remains feature-flag gated
- autonomy operates on `TaskSpec`
- budget validation and budget remaining output added
- cycle, runtime, and mutation-step budgets enforced before pending-plan creation
- failed mutation execution rolls back changed files
- rollback deduplicates repeated edits to the same path
- autonomy and rollback decision events are audited
- Sprint F acceptance-lock tests added
- full suite passed: `108 passed`

Command surface:
- `task.autonomy`
- `task.plan`
- `plan.submit`
- `plan.approve`
- `plan.execute`

Security boundary:
- no new direct execution surface
- no approval bypass
- no autonomous tool execution outside `plan.execute`
- no workspace boundary expansion
- no hidden supervisor state

Deferred to Sprint G:
- multi-cycle continuation orchestration
- supervisor state graph
- strategy/evaluation loop
- autonomous continuation policy after approval

---


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
