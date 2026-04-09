# Instruction-Only Operating Guide

## Overview
This repository now runs in instruction-first mode for orchestration and SDLC control.
Python code is limited to the `backend/` folder.

## Where Control Logic Lives
- Global contract: `claude.md`
- SDLC execution controller: `memory/plan.md`
- Role instructions: `agents/*.md`
- Orchestrator coordination contract: `orchestrator/orchestrator.md`
- Tool usage contract: `mcp/mcp.md`
- Terminal interaction contract: `cli/cli.md`

## How To Operate
1. Add or update requirement context in memory artifacts.
2. Use the orchestrator instruction contract to route by phase.
3. Execute tools only via the MCP instruction contract.
4. Update `memory/plan.md` after each major action.

## Backend Runtime
Run backend API locally:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Build container:

```bash
docker compose up --build
```

## Non-Negotiables
- Do not add Python code outside `backend/`.
- Do not skip SDLC phases.
- Do not fabricate tool outputs.
