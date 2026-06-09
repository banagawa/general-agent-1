# Sprint H Closeout v6 — Workspace Intelligence Layer

Status: complete through Slice 7

## Goal

Give the agent structural understanding of the repository while preserving the authority boundary.

Workspace intelligence may describe the repository. It must not grant authority.

## Source PRs and commits

| PR | Merge commit | Area | Current-state meaning |
|---:|---:|---|---|
| #22 | `49eabfc` | Workspace intelligence authority boundary | Documented advisory-only workspace intelligence before implementation. |
| #23 | `e396a53` | Sprint H Slice 1 workspace graph foundation | ArtifactIDs, read-only Python workspace graph, module/function/test/import discovery, graph rebuild audit. |
| #24 | `48b1ce4` | Sprint H Slice 2 dependency-aware impact analysis | Module import impact selection and changed-test-file preservation. |
| #25 | `44d815a` | Sprint H Slice 3 artifact index lookups | Deterministic FILE/MODULE/FUNC/TEST ArtifactID lookup on the graph. |
| #26 | `9fc8a96` | Sprint H Slice 4 graph query APIs | find_file/find_module/find_function/find_test convenience helpers. |
| #27 | `a3df60a` | Sprint H Slice 5 static call graph mapping | AST static call graph extraction and calls_from/called_by APIs. |
| #28 | `efcefce` | Sprint H Slice 6 function-level impact propagation | impacted_tests_for_functions over reverse static call graph edges. |
| #29 | `f79a6e0` | Sprint H Slice 7 intelligent test selection | TestSelection and select_tests_for_changes combining path/module/function impact with full-suite fallback recommendation. |


## Delivered capability

The workspace intelligence layer now supports:

- `ArtifactID` parsing, formatting, and fail-closed validation.
- `WorkspaceGraph` construction from Python files under `workspace_root`.
- file, module, function, and test ArtifactID metadata.
- changed-path and changed-module impacted-test selection.
- deterministic ArtifactID lookup and convenience query helpers.
- static function call edges from AST.
- reverse call-graph propagation from changed `FUNC` ArtifactIDs.
- `TestSelection` result metadata.
- `select_tests_for_changes(...)` as the single advisory test-selection entry point.

## Security boundary

No Sprint H slice added:

- ToolGateway changes.
- policy changes.
- validator or executor changes.
- capability expansion.
- autonomy expansion.
- automatic test execution.
- plan mutation.
- workspace mutation authority from graph results.
- external indexing services.

## Current selector behavior

`select_tests_for_changes(...)` composes existing graph intelligence:

```text
changed paths/functions
        ↓
workspace graph
        ↓
path/module impact + function impact
        ↓
deterministic test recommendations
        ↓
full-suite fallback recommendation when precise selection is unavailable
```

The selector is advisory only. It recommends tests; it does not run tests.

## Validation

Slice PRs recorded targeted and full-suite validation. This closeout is documentation-only and should be validated with:

```text
python -m pytest -q
```
