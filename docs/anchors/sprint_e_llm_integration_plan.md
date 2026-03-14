# sprint_e_llm_integration_plan.md

Status: Sprint E Extension

Governing docs:

- SECURITY.md
- CONTRIBUTING.md
- docs/anchors/security-invariants.md

---

## Purpose

Introduce planner assistance without changing the execution security model.

---

## Security Alignment

Execution spine remains:

Orchestrator → AgentLoop → execute_step → ToolGateway → PolicyEngine → Tool

Planner may:

- normalize tasks
- generate PLAN JSON
- generate summaries

Planner may not:

- execute tools
- write files
- bypass approval
- bypass ToolGateway

---

## Execution Flow

task → TaskSpec → planner → plan.submit → plan.approve → plan.execute