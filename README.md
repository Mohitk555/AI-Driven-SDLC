# AI Engineering OS for Insurance Platform — Updated Tutorial (Instruction-First)

This tutorial reflects the current architecture:

- Orchestration and SDLC control are instruction-driven via Markdown contracts.
- Python code exists only under `backend/`.
- Root-level Python orchestrator/MCP/CLI runtime files have been removed.

---

## 1. What Changed

The project moved from a Python-orchestrator runtime to an instruction-first operating model.

Current control plane artifacts:

- `claude.md` — global operating contract
- `memory/constitution.md` — top governance
- `memory/plan.md` — SDLC execution controller + action log
- `orchestrator/orchestrator.md` — orchestration contract
- `agents/*.md` — role instructions
- `mcp/mcp.md` — tool execution contract
- `cli/cli.md` — terminal interaction contract

Backend API runtime remains in:

- `backend/main.py`
- `backend/routers/*`
- `backend/models.py`, `backend/schemas.py`, etc.

---

## 2. Prerequisites

| Requirement | Minimum Version |
|------------|------------------|
| Python | 3.11+ |
| pip | 23+ |
| Docker (optional) | 24+ |
| Docker Compose (optional) | 2.20+ |

Optional integrations (instruction contracts reference these):

- Jira Cloud API token
- GitHub PAT
- Slack bot token
- Google Calendar API credentials

---

## 3. Install & Run (Backend Only)

### Local run

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Server URL: `http://127.0.0.1:8000`

### Verify

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok","service":"backend"}
```

---

## 4. Docker Run

```bash
docker compose up --build
```

Current compose services:

- `backend` (FastAPI)
- `postgres`

---

## 5. Current API Surface

The old orchestrator endpoints (`/api/v1/chat`, `/api/v1/pipeline/*`, `/ws/chat`, `/api/v1/tools/execute`) are no longer part of the active Python runtime.

Current backend endpoints are provided by:

- `backend/routers/auth_router.py` → `/api/v1/auth/*`
- `backend/routers/claims_router.py` → `/api/v1/claims/*`
- `backend/main.py` → `/health`

---

## 6. Instruction-First SDLC Operation

Use the following sequence for autonomous SDLC execution in instruction mode:

1. Read `memory/constitution.md`
2. Read `memory/plan.md` (current phase + blockers)
3. Read `orchestrator/orchestrator.md` (routing and envelope rules)
4. Route to phase agent instruction (`agents/*.md`)
5. Execute tools according to `mcp/mcp.md`
6. Append mandatory action log entry to `memory/plan.md`

Strict state machine:

`IDLE -> REQUIREMENTS -> ARCHITECTURE -> TASKS -> DEVELOPMENT -> TESTING -> DEPLOYMENT -> DONE`

---

## 7. Role Instructions

Defined in:

- `agents/pm_agent.md`
- `agents/techlead_agent.md`
- `agents/scrum_agent.md`
- `agents/dev_be_agent.md`
- `agents/dev_fe_agent.md`
- `agents/qa_agent.md`
- `agents/devops_agent.md`

Each role is instruction-only and must produce deterministic structured outputs aligned with the output contract in `claude.md`.

---

## 8. Tooling Contract (Instruction-Level)

Tool policy now lives in `mcp/mcp.md`.

Domains:

- `jira.*`
- `github.*`
- `slack.*`
- `calendar.*`

Required execution behavior:

- No fabricated tool results
- Retry transient failures (up to policy limit)
- Record tool outcomes in `memory/plan.md`
- Trigger human intervention only under policy

---

## 9. Memory Artifacts

Primary shared artifacts:

- `memory/requirements.md`
- `memory/user_stories.md`
- `memory/architecture.md`
- `memory/tasks.md`
- `memory/test_cases.md`
- `memory/decisions.md`
- `memory/plan.md`

Rule: read before write, then append deterministic updates with phase/objective/validation/tool results/blockers.

---

## 10. Troubleshooting (Current Architecture)

### Backend import/runtime issues

```bash
python -m compileall backend
```

### Dependency issues

```bash
pip install -r backend/requirements.txt
```

### Port already in use

Windows:

```powershell
$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conn) { Stop-Process -Id $conn.OwningProcess -Force }
```

### Legacy command confusion

If you see references to `orchestrator.main:app` or `/api/v1/chat`, those belong to the retired runtime model and should not be used.

---

## 11. Migration Notes

- Removed: root Python orchestration runtime (`orchestrator/*.py`, `mcp/**/*.py`, `cli/*.py`)
- Removed: `pyproject.toml`
- Added: `backend/requirements.txt`
- Added: `docs/INSTRUCTION_MODE.md`
- Updated: `Dockerfile` to install dependencies from `backend/requirements.txt`

---

## 12. Quick Start Checklist

- [ ] Fill `.env` values for backend and optional integrations
- [ ] `pip install -r backend/requirements.txt`
- [ ] `uvicorn backend.main:app --reload`
- [ ] Verify `/health`
- [ ] Drive SDLC through instruction files + `memory/plan.md`

---

Last updated: 2026-04-05
Version: 2.0.0 (instruction-first)
