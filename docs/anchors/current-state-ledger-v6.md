# Current State Ledger v6

Status: documentation reconciliation anchor

Purpose: reconcile non-Python documentation with merged commits and PRs through Sprint H Slice 7.

This file is descriptive only. It does not create tool authority, policy authority, execution authority, or workspace mutation authority.

## Source ledger

| PR | Merge commit | Area | Current-state meaning |
|---:|---:|---|---|
| #10 | `da5d860` | Worktree runtime resolution hotfix | Clarified runtime/app root semantics so cwd does not define workspace authority. |
| #11 | `7f6f552` | Worktree test-root inference | Supported app/workspace root separation during worktree test execution. |
| #12 | `e5e0327` | Sprint G deterministic improvement engine | CycleOutcome, inert strategies/proposals, append-only registry, deterministic proposal generation, post-cycle hook, TEST_RUN cwd modes. |
| #13 | `52c05fb` | TEST_RUN allowlist and mutation approval validation | Constrained TEST_RUN command shapes and validated mutation tool/file-state alignment at approval time. |
| #14 | `b706674` | Path validation, capability scope, storage characterization | Hardened path hygiene and scoped capability validation; characterized storage behavior. |
| #15 | `9213276` | Runtime-state ownership and fingerprint exclusion | Documented runtime-state ownership and added future fingerprint exclusion bridge. |
| #16 | `a6a61e5` | Runtime bookkeeping outside target worktree | Moved audit/capability/pending-patch runtime bookkeeping under workspace/agent_runtime/<workspace_name>. |
| #17 | `7f4a07a` | Runtime history ownership and health reporting | Moved plan lifecycle artifacts to runtime-state root and added report-only runtime history health. |
| #18 | `e67b610` | Rollback workspace boundary recheck | Rechecked rollback snapshot paths against workspace boundary before restore/delete. |
| #19 | `21eb805` | Root authority invariant tests | Proved cwd does not become workspace authority and app_root cannot become workspace_root. |
| #20 | `34bde3c` | ToolGateway chokepoint invariant guards | Guarded against direct filesystem, policy, or command execution paths outside ToolGateway. |
| #21 | `54745fb` | Denial audit observability | Verified representative denial paths emit audit events. |
| #22 | `49eabfc` | Workspace intelligence authority boundary | Documented advisory-only workspace intelligence before implementation. |
| #23 | `e396a53` | Sprint H Slice 1 workspace graph foundation | ArtifactIDs, read-only Python workspace graph, module/function/test/import discovery, graph rebuild audit. |
| #24 | `48b1ce4` | Sprint H Slice 2 dependency-aware impact analysis | Module import impact selection and changed-test-file preservation. |
| #25 | `44d815a` | Sprint H Slice 3 artifact index lookups | Deterministic FILE/MODULE/FUNC/TEST ArtifactID lookup on the graph. |
| #26 | `9fc8a96` | Sprint H Slice 4 graph query APIs | find_file/find_module/find_function/find_test convenience helpers. |
| #27 | `a3df60a` | Sprint H Slice 5 static call graph mapping | AST static call graph extraction and calls_from/called_by APIs. |
| #28 | `efcefce` | Sprint H Slice 6 function-level impact propagation | impacted_tests_for_functions over reverse static call graph edges. |
| #29 | `f79a6e0` | Sprint H Slice 7 intelligent test selection | TestSelection and select_tests_for_changes combining path/module/function impact with full-suite fallback recommendation. |


## Current merged state

### Sprint G

Sprint G is complete. The deterministic improvement engine foundation includes:

- `CycleOutcome` outcome normalization.
- inert `Strategy` and `StrategyProposal` data models.
- append-only strategy registry records.
- deterministic proposal generation from execution outcomes.
- post-cycle proposal integration after execution summary/failure-envelope creation.
- explicit `TEST_RUN` cwd selection for `workspace` and `app`.

Strategy behavior remains data-only. There is no automatic strategy installation, no strategy-driven execution, no policy mutation, no plan schema expansion, and no autonomy expansion.

### Pre-Sprint-H hardening

The hardening sequence between Sprint G and Sprint H is part of the current architecture baseline. It includes:

- TEST_RUN allowlisting.
- approval-time mutation/file-state validation.
- path hygiene and capability-scope hardening.
- runtime-state ownership and fingerprint boundaries.
- runtime bookkeeping outside the target worktree.
- plan lifecycle artifacts under runtime-state root.
- read-only runtime history health reporting.
- rollback workspace-boundary rechecks.
- root authority invariants.
- ToolGateway chokepoint guard tests.
- denial audit observability.
- workspace intelligence advisory authority boundary.

### Sprint H

Sprint H is complete through Slice 7. The workspace intelligence layer now includes:

- stable ArtifactID model: `FILE::path`, `MODULE::path`, `FUNC::path::symbol`, `TEST::path::test_name`.
- read-only workspace graph construction from Python files inside `workspace_root`.
- dependency-aware impacted-test selection from changed paths/modules.
- deterministic ArtifactID lookup and graph query helpers.
- static call graph mapping from Python AST.
- function-level impact propagation from changed `FUNC` ArtifactIDs.
- intelligent advisory test selection through `select_tests_for_changes(...)`.

Workspace intelligence remains advisory only. It may recommend impacted files or tests. It must not grant permission, bypass ToolGateway or PolicyEngine, mutate plans, execute tests, expand capabilities, or authorize workspace mutation.

## Governing invariants preserved

- ToolGateway remains the execution choke point.
- Policy remains deny-by-default.
- Workspace boundary remains enforced.
- Mutations remain typed and approval-bound: `PATCH_APPLY`, `PATCH_EDIT`, `FILE_CREATE`.
- Audit remains append-only.
- Strategies remain inert data.
- Workspace intelligence remains advisory data.
