# System State v1

This document describes the architecture after completion of Sprint D.

---

# Core Architecture

Execution pipeline:

AgentLoop
 → PlanExecutor
 → execute_step
 → ToolGateway
 → PolicyEngine
 → Tool

All tool execution passes through ToolGateway.

---

# Security Invariants

The system maintains the following invariants:

- ToolGateway is the single execution choke point
- deny-by-default enforcement
- workspace boundary isolation
- patch-only file writes
- append-only audit logging

---

# Capability Enforcement

Every tool call requires a capability token.

Tokens:
- short-lived
- scoped
- validated by the PolicyEngine

Tokens are issued automatically for approved plan steps.

---

# Plan Execution Model

Execution requires an approved plan.

Commands:
plan.submit
plan.approve
plan.execute

Execution lifecycle:
plan.submit → validate_plan → store_pending_plan
plan.approve → mark_plan_approved
plan.execute → execute_step → ToolGateway

---

# Audit Lifecycle

PLAN_CREATED
PLAN_APPROVED
PLAN_EXECUTION_STARTED
PLAN_EXECUTION_FINISHED
PLAN_EXECUTION_DENIED
PLAN_EXECUTION_FAILED

Audit logs are append-only.

---

# Sprint Status

| Sprint | Status |
|------|------|
Sprint A | Complete |
Sprint B | Complete |
Sprint C | Complete |
Sprint D | Complete |

---

# Next Phase

Sprint E introduces deterministic development loops.