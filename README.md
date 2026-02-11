# general-agent-1
# Internal Agent

Hybrid supervised/autonomous internal assistant with sandboxed local file access and revocable permissions.

## Mission (v1)

This agent exists to safely read, summarize, and propose changes to local workspace files.

It is not allowed to modify files, run commands, or access external systems without explicit permission.

---

## Design Principles

- Deny by default
- All tool access goes through a Tool Gateway
- Permissions are scoped, time-bound, and revocable
- Writes use patch/diff-based edits
- All actions are logged

---

## Initial Scope (MVP)

Workspace: (to be defined in config)

First job:
- Find files and summarize their contents

No write capability yet.
No command execution yet.
No network access.

---

## Architecture Overview

User → Orchestrator → Tool Gateway → Policy Engine → Sandbox Runtime

The model never directly touches the filesystem.

---

## Current Status

Day 1: Repo initialized.
Structure scaffolded.
No real functionality yet.

---

## How to Run (Placeholder)

```bash
python main.py "summarize docs"
