# Sprint G Closeout — Deterministic Improvement Engine Foundation

Status: Complete

Branch:
`sprint-g-deterministic-improvement-engine`

Goal:
Allow the agent to improve development strategy across cycles using deterministic, measurable execution outcomes while preserving approval gates, workspace isolation, deny-by-default policy, and append-only auditability.

Delivered:
- `CycleOutcome` deterministic outcome vocabulary
- inert `Strategy` and `StrategyProposal` data models
- append-only `StrategyRegistry`
- deterministic proposal generation from execution outcomes
- post-cycle proposal hook after summary/failure-envelope creation
- explicit `TEST_RUN` cwd selector for app-root and workspace-root tests
- regression tests for outcomes, strategy models, registry, proposal generation, integration behavior, and TEST_RUN cwd selection

Security boundary:
- strategies are data only
- no automatic strategy installation
- no strategy-driven tool execution
- no strategy-driven policy mutation
- no strategy-driven plan schema modification
- no autonomy expansion
- registry records are append-only
- proposal generation does not alter execution outcome

Runtime root model:
- `app_root` is the runtime/security-code authority
- `workspace_root` is the mutation and plan target
- `TEST_RUN` may use only `cwd: "workspace"` or `cwd: "app"`
- raw cwd paths are forbidden

Operator notes:
- runtime artifacts under `plans/` are execution artifacts and should not be committed as source
- `_pytest_fs_write_tokens/` is test residue and should not be committed
- source commits should include only code, tests, and documentation

Validation:
- full pytest suite passed after Sprint G implementation
