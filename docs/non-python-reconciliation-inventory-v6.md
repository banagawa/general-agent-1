# Non-Python Documentation Reconciliation Inventory v6

Status: current-state reconciliation inventory

Purpose: record how non-Python repository documents were reconciled against merged PRs and commits.

## Source basis

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


## Updated by this plan

- `README.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `audit/README.md`
- `docs/audit_token_storage_boundary.md`
- `docs/general_plan_submit_constraints.txt`
- `docs/anchors/architecture-contract.md`
- `docs/anchors/capability-model.md`
- `docs/anchors/security-invariants.md`
- `docs/anchors/sprint-history.md`
- `docs/anchors/system-state-v1.md`
- `docs/anchors/workspace-intelligence-boundary.md`
- `docs/anchors/write-lifecycle.md`
- `docs/sprints/HISTORICAL_WAIVERS.md`
- `docs/sprints/sprint-g-closeout.md`
- `docs/sprints/sprint-h-workspace-intelligence-slice-1.md`
- `roadmap_governance_addendum.md`
- `tests/README.md`

## Added by this plan

- `docs/anchors/current-state-ledger-v6.md`
- `docs/sprints/pre-sprint-h-hardening-closeout-v6.md`
- `docs/sprints/sprint-h-closeout-v6.md`
- `docs/non-python-reconciliation-inventory-v6.md`

## Reviewed but not rewritten

These non-Python files are intentionally left as-is:

- `.gitignore`, `pytest.ini`, `requirements.txt`: configuration, not current-state narrative.
- historical Sprint A-E closeout documents: retained as historical artifacts unless explicitly listed above.
- generated runtime/plan/audit artifacts: not source documentation and should not be normalized in this pass.
- PDF historical anchors: not edited by executable JSON plan.

## Boundary

This reconciliation is documentation-only. It does not change Python source, policy, ToolGateway, validator, executor, capabilities, autonomy behavior, test selection behavior, or runtime behavior.
