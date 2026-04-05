# AI Engineering OS for Insurance Platform — Complete Tutorial

A step-by-step guide to setting up, running, and using the AI-driven SDLC system.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Installation & Setup](#3-installation--setup)
4. [Configuration — Environment Variables](#4-configuration--environment-variables)
5. [Starting the Server](#5-starting-the-server)
6. [Architecture Deep Dive](#6-architecture-deep-dive)
7. [Using the Chat API](#7-using-the-chat-api)
8. [Using the WebSocket API](#8-using-the-websocket-api)
9. [Intent Detection & Agent Routing](#9-intent-detection--agent-routing)
10. [Working with Agents](#10-working-with-agents)
    - [PM Agent](#101-pm-agent-product-manager)
    - [Tech Lead Agent](#102-tech-lead-agent)
    - [Scrum Master Agent](#103-scrum-master-agent)
    - [Backend Developer Agent](#104-backend-developer-agent)
    - [Frontend Developer Agent](#105-frontend-developer-agent)
    - [QA Agent](#106-qa-agent)
    - [DevOps Agent](#107-devops-agent)
11. [SDLC Workflow Engine](#11-sdlc-workflow-engine)
12. [MCP Tool System](#12-mcp-tool-system)
13. [Tool Integrations Reference](#13-tool-integrations-reference)
14. [Memory System](#14-memory-system)
15. [Constitution & Governance](#15-constitution--governance)
16. [State Management & Sessions](#16-state-management--sessions)
17. [Docker Deployment](#17-docker-deployment)
18. [End-to-End Walkthrough](#18-end-to-end-walkthrough)
19. [Autonomous Pipeline](#19-autonomous-pipeline)
20. [Scheduler — Automated Slack Updates](#20-scheduler--automated-slack-updates)
21. [Human Intervention & Escalation](#21-human-intervention--escalation)
22. [Troubleshooting](#22-troubleshooting)
23. [API Reference](#23-api-reference)

---

## 1. Overview

The AI Engineering OS is a platform that simulates a real-world software organization using multiple AI agents. A human stakeholder interacts with the system via natural language, and the system:

- Detects intent from the message
- Routes the request to the appropriate AI agent (PM, Tech Lead, Scrum Master, Developers, QA, DevOps)
- Agents collaborate through a central orchestrator
- Agents use external tools (Jira, GitHub, Slack, Google Calendar) via the MCP layer
- The system manages the full SDLC lifecycle for an Insurance Operating System (InsureOS)

**Tech Stack:**
- Backend/Orchestrator: Python 3.11+ with FastAPI
- Frontend (target project): Next.js with TypeScript
- Database: PostgreSQL 16
- AI: Anthropic Claude API
- Tools: Jira, GitHub, Slack, Google Calendar via MCP

---

## 2. Prerequisites

Before you begin, ensure you have:

| Requirement | Minimum Version |
|------------|----------------|
| Python | 3.11+ |
| pip | 23.0+ |
| Git | 2.40+ |
| Docker (optional) | 24.0+ |
| Docker Compose (optional) | 2.20+ |

Optional (for tool integrations):
- Jira Cloud account with API token
- GitHub account with Personal Access Token
- Slack workspace with a Bot token
- Google Cloud project with Calendar API enabled

---

## 3. Installation & Setup

### Step 1: Clone or navigate to the project

```bash
cd /path/to/spec-driven-sdlc
```

### Step 2: Create a virtual environment (recommended)

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### Step 3: Install dependencies

```bash
# Install with dev dependencies
pip install -e ".[dev]"
```

This installs:
- **Core:** fastapi, uvicorn, pydantic, httpx, websockets, python-dotenv, anthropic
- **Dev:** pytest, pytest-asyncio, pytest-cov, ruff, mypy

### Step 4: Copy environment config

```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys (see next section).

---

## 4. Configuration — Environment Variables

The `.env` file controls all external service connections. Here is every variable:

### Application Settings

| Variable | Description | Default |
|----------|------------|---------|
| `APP_ENV` | Environment name | `development` |
| `APP_PORT` | Server port | `8000` |
| `APP_LOG_LEVEL` | Logging level (DEBUG, INFO, WARN, ERROR) | `INFO` |

### AI / LLM

| Variable | Description | Required |
|----------|------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | Yes (for AI responses) |

### Jira Integration

| Variable | Description | Example |
|----------|------------|---------|
| `JIRA_BASE_URL` | Your Jira Cloud URL | `https://mycompany.atlassian.net` |
| `JIRA_EMAIL` | Jira account email | `dev@company.com` |
| `JIRA_API_TOKEN` | Jira API token ([generate here](https://id.atlassian.com/manage-profile/security/api-tokens)) | `ATATT3x...` |
| `JIRA_PROJECT_KEY` | Default project key | `INS` |

### GitHub Integration

| Variable | Description | Example |
|----------|------------|---------|
| `GITHUB_TOKEN` | Personal Access Token ([generate here](https://github.com/settings/tokens)) | `ghp_xxxx` |
| `GITHUB_OWNER` | GitHub org or username | `my-org` |
| `GITHUB_REPO` | Repository name | `insure-os` |

### Slack Integration

| Variable | Description | Example |
|----------|------------|---------|
| `SLACK_BOT_TOKEN` | Slack Bot OAuth Token | `xoxb-xxxx` |
| `SLACK_DEFAULT_CHANNEL` | Default channel ID | `C0123456789` |

### Google Calendar Integration

| Variable | Description | Example |
|----------|------------|---------|
| `GOOGLE_CALENDAR_ID` | Calendar ID | `primary` |
| `GOOGLE_API_KEY` | Google API key | `AIzaSy...` |

### Database

| Variable | Description | Default |
|----------|------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/insure_os` |

> **Note:** The system works without external tool credentials — tool calls will return errors but the orchestrator and agents function normally. You can add credentials incrementally.

---

## 5. Starting the Server

### Development mode (with hot-reload)

```bash
uvicorn orchestrator.main:app --reload
```

The server starts at `http://127.0.0.1:8000`.

### Production mode

```bash
uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Verify the server is running

```bash
# Health check (shallow)
curl http://localhost:8000/health
# Response: {"status": "ok"}

# Readiness check (deep — verifies state manager)
curl http://localhost:8000/ready
# Response: {"status": "ready", "state_loaded": true}
```

---

## 6. Architecture Deep Dive

The system has 4 layers:

```
┌──────────────────────────────────────────────────────────┐
│                   INTERFACE LAYER                        │
│          REST API (POST /api/v1/chat)                    │
│          WebSocket (WS /ws/chat)                         │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│                 ORCHESTRATOR LAYER                        │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐  ┌────────┐  │
│  │  Router  │  │ Workflow │  │   State    │  │ Models │  │
│  │(intent   │  │ Engine   │  │  Manager   │  │(Pydan- │  │
│  │detection)│  │(SDLC     │  │(persistence│  │ tic v2)│  │
│  │          │  │ pipeline) │  │  + locking)│  │        │  │
│  └─────────┘  └──────────┘  └────────────┘  └────────┘  │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│                    AGENT LAYER                            │
│  ┌────┐ ┌──────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌──┐ ┌──┐│
│  │ PM │ │Scrum │ │TechLead│ │Dev BE│ │Dev FE│ │QA│ │DO││
│  └────┘ └──────┘ └────────┘ └──────┘ └──────┘ └──┘ └──┘│
│                 All inherit BaseAgent                    │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│                  EXECUTION LAYER                          │
│  ┌──────────────────────────────────────────────┐        │
│  │              MCP Server                       │        │
│  │  ┌──────┐ ┌────────┐ ┌───────┐ ┌──────────┐ │        │
│  │  │ Jira │ │ GitHub │ │ Slack │ │ Calendar │ │        │
│  │  └──────┘ └────────┘ └───────┘ └──────────┘ │        │
│  └──────────────────────────────────────────────┘        │
│  ┌──────────────┐  ┌──────────┐  ┌────────────────┐      │
│  │   Memory     │  │ Database │  │  CI/CD         │      │
│  │  (markdown)  │  │(Postgres)│  │  (GitHub       │      │
│  │              │  │          │  │   Actions)     │      │
│  └──────────────┘  └──────────┘  └────────────────┘      │
└──────────────────────────────────────────────────────────┘
```

### File Structure

```
spec-driven-sdlc/
├── orchestrator/
│   ├── __init__.py           # Exports: AgentRouter, StateManager, WorkflowEngine, models
│   ├── main.py               # FastAPI app, REST + WebSocket endpoints
│   ├── router.py             # Intent detection, agent routing
│   ├── models.py             # Pydantic models (ChatRequest, AgentResponse, ToolCall, etc.)
│   ├── workflow_engine.py    # 6-stage SDLC pipeline
│   └── state_manager.py      # Thread-safe state persistence to JSON
├── agents/
│   ├── __init__.py           # Exports all agents + AGENT_REGISTRY dict
│   ├── base_agent.py         # Abstract base class for all agents
│   ├── pm_agent.py           # Product Manager
│   ├── scrum_agent.py        # Scrum Master
│   ├── techlead_agent.py     # Tech Lead / Architect
│   ├── dev_be_agent.py       # Backend Developer
│   ├── dev_fe_agent.py       # Frontend Developer
│   ├── qa_agent.py           # QA Engineer
│   └── devops_agent.py       # DevOps Engineer
├── mcp/
│   ├── __init__.py           # Exports MCPServer
│   ├── mcp_server.py         # Tool registry, permission enforcement
│   └── tools/
│       ├── __init__.py       # Exports all tool classes
│       ├── base_tool.py      # Abstract base for tools
│       ├── jira_tool.py      # Jira REST API (5 actions)
│       ├── github_tool.py    # GitHub REST API (5 actions)
│       ├── slack_tool.py     # Slack Web API (2 actions)
│       └── calendar_tool.py  # Google Calendar API (2 actions)
├── memory/                   # Shared knowledge base
│   ├── constitution.md       # Supreme rulebook (14 sections)
│   ├── requirements.md       # PM Agent output
│   ├── user_stories.md       # PM Agent output
│   ├── architecture.md       # Tech Lead output
│   ├── tasks.md              # Scrum Agent output
│   ├── test_cases.md         # QA Agent output
│   ├── decisions.md          # Decision log (all agents)
│   └── system_state.json     # Persisted system state (auto-generated)
├── frontend/                 # Next.js app (generated by Dev FE Agent)
├── backend/                  # FastAPI app (generated by Dev BE Agent)
├── docs/                     # Documentation
├── pyproject.toml            # Python project config
├── Dockerfile                # Multi-stage production build
├── docker-compose.yml        # Orchestrator + PostgreSQL
├── .env.example              # Environment template
└── .gitignore
```

---

## 7. Using the Chat API

The primary interface is the `POST /api/v1/chat` endpoint.

### Request Format

```json
{
  "message": "Your natural language request (1-4096 characters)",
  "session_id": "optional-uuid-to-continue-a-session"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | Natural language input (1-4096 chars) |
| `session_id` | string or null | No | UUID to continue an existing session. If null, a new session is created. |

### Response Format

```json
{
  "session_id": "6eb6759e-a9c9-437a-a9e5-d15abe9f6e11",
  "intent": "dev_backend",
  "agent_id": "dev_backend_agent",
  "message": "Agent's response text...",
  "data": null,
  "tool_calls": [],
  "status": "completed",
  "timestamp": "2026-04-05T10:30:00.000000"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Session UUID (reuse this to continue the conversation) |
| `intent` | string | Detected intent type (see [Section 9](#9-intent-detection--agent-routing)) |
| `agent_id` | string | Which agent handled the request |
| `message` | string | Human-readable response from the agent |
| `data` | any or null | Structured data (tool results, generated artifacts, etc.) |
| `tool_calls` | array | List of tool calls the agent wants to execute |
| `status` | string | `completed`, `in_progress`, `failed`, or `blocked` |
| `timestamp` | string | ISO 8601 timestamp |

### Examples

**Example 1: Define requirements**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "We need a claims management module where policyholders can submit claims, upload documents, and track claim status"
  }'
```

**Example 2: Check sprint status**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the current sprint status?",
    "session_id": "6eb6759e-a9c9-437a-a9e5-d15abe9f6e11"
  }'
```

**Example 3: Build a feature**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Build the backend API for the claims module"
  }'
```

**Example 4: Design architecture**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Design the system architecture for policy management with database schema"
  }'
```

**Example 5: Generate tests**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Generate test cases for the claims API endpoints"
  }'
```

**Example 6: Set up deployment**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create Docker configuration and CI/CD pipeline for the project"
  }'
```

---

## 8. Using the WebSocket API

For real-time streaming communication, connect via WebSocket.

### Endpoint

```
ws://localhost:8000/ws/chat
```

### Protocol

**Client sends:**
```json
{
  "message": "Your request here",
  "session_id": "optional-uuid"
}
```

**Server responds:**
```json
{
  "session_id": "auto-generated-uuid",
  "intent": "requirements",
  "agent_id": "pm_agent",
  "message": "Agent's response...",
  "data": null,
  "tool_calls": [],
  "status": "completed",
  "timestamp": "2026-04-05T10:30:00.000000"
}
```

### JavaScript Example

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/chat");
let sessionId = null;

ws.onopen = () => {
  ws.send(JSON.stringify({
    message: "We need a claims management system",
    session_id: sessionId
  }));
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  sessionId = response.session_id; // Save for follow-up messages
  console.log(`[${response.agent_id}] ${response.message}`);
};

// Send follow-up message
function sendMessage(text) {
  ws.send(JSON.stringify({
    message: text,
    session_id: sessionId
  }));
}
```

### Python Example

```python
import asyncio
import json
import websockets

async def chat():
    async with websockets.connect("ws://localhost:8000/ws/chat") as ws:
        # Send request
        await ws.send(json.dumps({
            "message": "Design the architecture for claims module",
            "session_id": None
        }))

        # Receive response
        response = json.loads(await ws.recv())
        print(f"[{response['agent_id']}] {response['message']}")

        # Continue conversation
        await ws.send(json.dumps({
            "message": "Now create sprint tasks for it",
            "session_id": response["session_id"]
        }))
        response2 = json.loads(await ws.recv())
        print(f"[{response2['agent_id']}] {response2['message']}")

asyncio.run(chat())
```

---

## 9. Intent Detection & Agent Routing

The router analyzes your message using keyword/pattern matching and routes to the appropriate agent.

### Intent Categories & Keywords

| Intent | Routed To | Trigger Keywords |
|--------|-----------|-----------------|
| **requirements** | PM Agent | requirement, feature, user story, stakeholder, need, scope, prd, epic, acceptance criteria |
| **architecture** | Tech Lead Agent | architecture, system design, database design, schema, erd, tech stack, data model, microservice, api design, api contract |
| **task_planning** | Scrum Master Agent | sprint, status, ticket, jira, backlog, kanban, velocity, standup, plan, task, story point |
| **dev_frontend** | Frontend Dev Agent | frontend, react, next.js, component, ui, ux, css, tailwind, page, layout, dashboard |
| **dev_backend** | Backend Dev Agent | build, code, implement, develop, backend, endpoint, service, model, migration, fastapi, crud, api, database |
| **qa** | QA Agent | tests, qa, bug, validate, quality, coverage, regression, e2e, unit tests, integration tests |
| **devops** | DevOps Agent | deploy, ci, cd, docker, pipeline, kubernetes, k8s, terraform, helm, monitor, infra as code |
| **general** | PM Agent (fallback) | *(no match)* |

### How Routing Works

1. Your message is converted to lowercase
2. Each intent's keyword list is checked using regex word boundaries
3. The intent with the most keyword matches wins
4. If no keywords match, the message falls back to the PM Agent
5. The router returns an `AgentResponse` with `agent_id`, `intent`, and `original_message`

### Example Routing Results

| Message | Detected Intent | Agent |
|---------|----------------|-------|
| "We need a claims feature" | requirements | pm_agent |
| "Design the database schema" | architecture | techlead_agent |
| "What is the sprint status?" | task_planning | scrum_agent |
| "Build the claims API endpoint" | dev_backend | dev_backend_agent |
| "Create a dashboard component" | dev_frontend | dev_frontend_agent |
| "Run integration tests" | qa | qa_agent |
| "Set up the Docker pipeline" | devops | devops_agent |
| "Hello" | general | pm_agent |

---

## 10. Working with Agents

All agents share a common interface defined in `BaseAgent`:

```
BaseAgent (Abstract)
├── agent_id: str           # Unique identifier
├── role: str               # Human-readable role name
├── permissions: list[str]  # Allowed tool actions
├── process(message, context) → AgentResponse  # Main entry point
├── load_constitution() → str                  # Reads constitution.md
├── read_memory(filename) → str                # Reads from memory/
├── write_memory(filename, content)            # Writes to memory/
├── create_tool_call(tool, input) → ToolCall   # Creates validated tool call
└── validate_output(output) → bool             # Validates against constitution
```

---

### 10.1 PM Agent (Product Manager)

| Property | Value |
|----------|-------|
| **Agent ID** | `pm_agent` |
| **Role** | Product Manager |
| **Permissions** | `jira.create_ticket` |
| **Memory Files** | `requirements.md`, `user_stories.md` |

**What it does:**
- Converts free-form stakeholder input into structured requirements
- Assigns MoSCoW priorities (Must Have, Should Have, Could Have, Won't Have)
- Generates user stories in standard format: *"As a [role], I want [goal], so that [benefit]"*
- Writes structured output to `memory/requirements.md` and `memory/user_stories.md`
- Creates Jira Epics for each major requirement

**Example interaction:**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "We need a claims management module where policyholders can submit insurance claims, upload supporting documents, and track the status of their claims in real-time"
  }'
```

**What the PM Agent produces:**

In `memory/requirements.md`:
```markdown
### REQ-001: Claims Submission
- Priority: Must Have
- Description: Policyholders can submit insurance claims through the platform
- Status: Draft

### REQ-002: Document Upload
- Priority: Must Have
- Description: Policyholders can upload supporting documents for claims
- Status: Draft

### REQ-003: Real-time Claim Tracking
- Priority: Should Have
- Description: Policyholders can track claim status in real-time
- Status: Draft
```

In `memory/user_stories.md`:
```markdown
### US-001 [Must Have]
As an insurance policyholder, I want to submit claims online,
so that I can initiate the claims process without visiting a branch.

### US-002 [Must Have]
As an insurance policyholder, I want to upload supporting documents,
so that I can provide evidence for my claim.

### US-003 [Should Have]
As an insurance policyholder, I want to track my claim status in real-time,
so that I know the progress without calling support.
```

**Tool calls it may return:**
```json
{
  "type": "tool_call",
  "tool": "jira.create_ticket",
  "input": {
    "summary": "Claims Management Module",
    "issue_type": "Epic",
    "project_key": "INS",
    "description": "Epic for claims management..."
  }
}
```

---

### 10.2 Tech Lead Agent

| Property | Value |
|----------|-------|
| **Agent ID** | `techlead_agent` |
| **Role** | Tech Lead |
| **Permissions** | `github.create_branch` |
| **Memory Files** | `architecture.md`, `decisions.md` |

**What it does:**
- Reads requirements from memory, designs system architecture
- Defines API contracts (OpenAPI-style endpoint definitions)
- Designs database schema with tables, columns, indexes, and constraints
- Records Architecture Decision Records (ADRs) in `decisions.md`
- Default tech stack: Next.js 14 + FastAPI + PostgreSQL 16 + Redis + JWT auth
- Default service components: Auth, Policy, Claims, User, Notification

**Example interaction:**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Design the system architecture for the claims module with API contracts and database schema"
  }'
```

**What it produces in `memory/architecture.md`:**
- Component breakdown with responsibilities
- API contracts (e.g., `POST /api/v1/claims`, `GET /api/v1/claims/{id}`)
- Database schema (tables, columns, types, constraints, indexes)
- Service interaction diagrams

**What it produces in `memory/decisions.md`:**
```markdown
### DEC-001: Use PostgreSQL for Claims Data
- Agent: techlead_agent
- Date: 2026-04-05
- Context: Need ACID-compliant storage for insurance claims
- Decision: PostgreSQL 16 with JSONB for flexible document metadata
- Rationale: Strong data integrity, excellent JSON support, mature ecosystem
- Alternatives Considered: MongoDB (rejected: weaker consistency guarantees)
```

---

### 10.3 Scrum Master Agent

| Property | Value |
|----------|-------|
| **Agent ID** | `scrum_agent` |
| **Role** | Scrum Master |
| **Permissions** | `jira.create_ticket`, `jira.update_ticket`, `jira.get_ticket`, `jira.get_sprint`, `slack.send_message`, `calendar.get_events` |
| **Memory Files** | `tasks.md` |

**What it does:**
- Creates sprint plans from user stories (default: 14-day sprints)
- Breaks stories into sub-tasks (backend, frontend, QA)
- Assigns default story points (5 per task)
- Reports sprint status by querying Jira
- Sends Slack notifications for sprint updates
- Checks calendar for upcoming meetings

**Example interactions:**

```bash
# Plan a sprint
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a sprint plan for the claims module user stories"}'

# Check sprint status
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the current sprint status?"}'

# Get ticket details
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the status of ticket INS-142?"}'
```

**What it produces in `memory/tasks.md`:**
```markdown
| ID | Title | Type | Priority | Story Points | Status |
|----|-------|------|----------|-------------|--------|
| TASK-001 | Implement claims submission API | Backend | High | 5 | To Do |
| TASK-002 | Create claims form component | Frontend | High | 5 | To Do |
| TASK-003 | Write claims API test cases | QA | Medium | 5 | To Do |
```

**Tool calls it may return:**
```json
[
  {
    "type": "tool_call",
    "tool": "jira.create_ticket",
    "input": {"summary": "Implement claims submission API", "issue_type": "Task"}
  },
  {
    "type": "tool_call",
    "tool": "slack.send_message",
    "input": {"text": "Sprint 1 has been planned with 6 tasks (30 story points)"}
  },
  {
    "type": "tool_call",
    "tool": "calendar.get_events",
    "input": {"max_results": 5}
  }
]
```

---

### 10.4 Backend Developer Agent

| Property | Value |
|----------|-------|
| **Agent ID** | `dev_be_agent` |
| **Role** | Backend Developer |
| **Permissions** | `github.create_branch`, `github.push_code`, `github.create_pr`, `jira.update_ticket` |
| **Output Directory** | `backend/` |

**What it does:**
- Reads architecture from memory to understand API contracts and DB schema
- Generates complete FastAPI application code:
  - `backend/main.py` — FastAPI app with router includes
  - `backend/routers/{module}.py` — CRUD endpoints with pagination
  - `backend/models/{module}.py` — Pydantic models (Create, Response variants)
  - `backend/services/{module}.py` — Service layer with business logic
  - `backend/config.py` — Configuration via `pydantic_settings.BaseSettings`
  - `backend/deps.py` — Dependency injection (DB sessions, auth)
- Creates feature branches, pushes code, opens PRs
- Updates Jira ticket status as work progresses

**Example interaction:**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Build the backend API endpoints for claims management"}'
```

**Tool calls it returns:**
```json
[
  {
    "type": "tool_call",
    "tool": "github.create_branch",
    "input": {"branch_name": "feature/INS-101-claims-api", "base_ref": "develop"}
  },
  {
    "type": "tool_call",
    "tool": "github.push_code",
    "input": {
      "file_path": "backend/routers/claims.py",
      "content": "...generated code...",
      "branch": "feature/INS-101-claims-api",
      "commit_message": "feat(claims): add claims CRUD endpoints"
    }
  },
  {
    "type": "tool_call",
    "tool": "github.create_pr",
    "input": {
      "title": "[INS-101] Add claims management API",
      "head": "feature/INS-101-claims-api",
      "base": "develop",
      "body": "Implements CRUD endpoints for claims..."
    }
  },
  {
    "type": "tool_call",
    "tool": "jira.update_ticket",
    "input": {"ticket_key": "INS-101", "fields": {"status": "In Review"}}
  }
]
```

---

### 10.5 Frontend Developer Agent

| Property | Value |
|----------|-------|
| **Agent ID** | `dev_fe_agent` |
| **Role** | Frontend Developer |
| **Permissions** | `github.create_branch`, `github.push_code`, `github.create_pr`, `jira.update_ticket` |
| **Output Directory** | `frontend/` |

**What it does:**
- Reads architecture from memory for API contracts and component needs
- Generates Next.js/React TypeScript code:
  - `frontend/src/app/layout.tsx` — Root layout with navigation
  - `frontend/src/app/page.tsx` — Home page
  - `frontend/src/components/{component}.tsx` — UI components (kebab-case files)
  - `frontend/src/lib/api.ts` — API client with `apiFetch()` utility
  - `frontend/src/hooks/use-api.ts` — TanStack Query hooks for data fetching
  - `frontend/src/types/index.ts` — TypeScript interfaces
- Creates branches, pushes code, opens PRs
- Updates Jira tickets

**Example interaction:**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create the frontend dashboard and claims form components"}'
```

---

### 10.6 QA Agent

| Property | Value |
|----------|-------|
| **Agent ID** | `qa_agent` |
| **Role** | QA Engineer |
| **Permissions** | `jira.create_ticket`, `jira.update_ticket` |
| **Memory Files** | `test_cases.md` |

**What it does:**
- Reads architecture and requirements to generate comprehensive test cases
- Creates three types of tests:
  - **API Tests** — endpoint validation (status codes, payloads, error handling)
  - **Acceptance Tests** — user story verification
  - **Security Tests** — auth, injection, CORS, rate limiting
- Validates architecture against requirements (finds gaps/inconsistencies)
- Generates pytest files: `tests/test_{resource}.py` with `tests/conftest.py`
- Logs bugs as Jira tickets when issues are found

**Example interaction:**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Generate test cases for the claims API and validate against requirements"}'
```

**What it produces in `memory/test_cases.md`:**
```markdown
### TC-001: Claims — POST /api/v1/claims returns 201
- Type: API
- Priority: Critical
- Status: Draft
- Linked Requirement: REQ-001

### TC-002: Claims — GET /api/v1/claims/{id} returns 404 for missing
- Type: API
- Priority: High
- Status: Draft
- Linked Requirement: REQ-003

### TC-003: Security — Claims endpoint rejects unauthenticated requests
- Type: Security
- Priority: Critical
- Status: Draft
```

---

### 10.7 DevOps Agent

| Property | Value |
|----------|-------|
| **Agent ID** | `devops_agent` |
| **Role** | DevOps Engineer |
| **Permissions** | `github.create_branch`, `github.push_code`, `github.create_pr` |

**What it does:**
- Generates Docker configurations:
  - `backend/Dockerfile` — Multi-stage Python 3.11 build
  - `frontend/Dockerfile` — Multi-stage Node 20 build
  - `docker-compose.yml` — Dev environment
  - `docker-compose.prod.yml` — Production environment
  - `.dockerignore`
- Generates CI/CD pipelines:
  - `.github/workflows/ci.yml` — Lint, test-backend, test-frontend, build
  - `.github/workflows/deploy.yml` — Staging & production deployment
- Creates deployment configs:
  - `deploy/nginx.conf` — Reverse proxy configuration
  - `deploy/.env.example` — Production environment template

**Example interaction:**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Set up Docker containers and CI/CD pipeline with GitHub Actions"}'
```

---

## 11. SDLC Workflow Engine

The workflow engine manages a 6-stage SDLC pipeline. Each stage has entry and exit criteria.

### Stages (in order)

```
REQUIREMENTS → ARCHITECTURE → TASK_PLANNING → DEVELOPMENT → TESTING → DEPLOYMENT
```

### Stage Criteria

| Stage | Entry Criteria | Exit Criteria |
|-------|---------------|---------------|
| **Requirements** | *(none — first stage)* | PRD document created; Stakeholder approval recorded |
| **Architecture** | Requirements stage completed | Architecture document created; API contracts defined |
| **Task Planning** | Architecture stage completed | Sprint backlog created; Tasks estimated |
| **Development** | Task planning stage completed | All sprint tasks completed; Code review passed |
| **Testing** | Development stage completed | All tests passing; Coverage targets met |
| **Deployment** | Testing stage completed | Deployment successful; Health checks passing |

### Querying Workflow State

```bash
curl http://localhost:8000/api/v1/workflow
```

Response:
```json
{
  "current_stage": "requirements",
  "stages_completed": [],
  "stage_criteria": {
    "requirements": {
      "entry": [],
      "exit": ["PRD document created", "Stakeholder approval recorded"]
    },
    "architecture": {
      "entry": ["Requirements stage completed"],
      "exit": ["Architecture document created", "API contracts defined"]
    }
  },
  "started_at": "2026-04-05T10:00:00",
  "updated_at": "2026-04-05T10:00:00"
}
```

### How Advancement Works

1. The workflow engine tracks which exit criteria have been completed for each stage
2. When all exit criteria for the current stage are met, `can_advance()` returns `true`
3. Calling `advance_stage()` moves to the next stage (if criteria are met)
4. Stages cannot be skipped — they must progress sequentially
5. Each stage maps to a primary agent:

| Stage | Primary Agent |
|-------|--------------|
| Requirements | PM Agent |
| Architecture | Tech Lead Agent |
| Task Planning | Scrum Agent |
| Development | Dev Backend Agent |
| Testing | QA Agent |
| Deployment | DevOps Agent |

---

## 12. MCP Tool System

The MCP (Model Context Protocol) layer provides a standardized interface for agents to interact with external tools.

### How It Works

1. Agents return `tool_call` objects in their responses (they do NOT execute tools directly)
2. The orchestrator passes tool calls to the MCP Server
3. MCP Server validates permissions, resolves the tool, and executes
4. Results are returned to the agent for final response generation

### Flow Diagram

```
Agent                    Orchestrator              MCP Server              External API
  │                          │                         │                       │
  │ ── AgentResponse ──────> │                         │                       │
  │    (with tool_calls)     │                         │                       │
  │                          │ ── execute(tool_call) ─> │                       │
  │                          │                         │ ── check_permission ─> │
  │                          │                         │ ── HTTP request ─────> │
  │                          │                         │ <── response ───────── │
  │                          │ <── ToolResult ──────── │                       │
  │ <── result ───────────── │                         │                       │
```

### Permission Matrix

Each agent has strict permissions on which tools they can use:

| Agent | Allowed Tools |
|-------|--------------|
| **PM Agent** | `jira.create_ticket` |
| **Scrum Agent** | `jira.*`, `slack.*`, `calendar.*` |
| **Tech Lead Agent** | `github.create_branch` |
| **Backend Dev Agent** | `github.*`, `jira.update_ticket` |
| **Frontend Dev Agent** | `github.*`, `jira.update_ticket` |
| **QA Agent** | `jira.create_ticket`, `jira.update_ticket` |
| **DevOps Agent** | `github.*` |

> Permissions use glob-style matching. `github.*` means all GitHub actions (create_branch, push_code, create_pr, etc.)

### Tool Call Format

Agents produce tool calls in this format:
```json
{
  "type": "tool_call",
  "tool": "jira.create_ticket",
  "input": {
    "summary": "Implement claims API",
    "issue_type": "Task",
    "description": "CRUD endpoints for claims management"
  }
}
```

### Tool Result Format

MCP returns results in this format:
```json
{
  "success": true,
  "data": {
    "key": "INS-101",
    "id": "10042",
    "self": "https://mycompany.atlassian.net/rest/api/3/issue/10042"
  },
  "error": null
}
```

---

## 13. Tool Integrations Reference

### 13.1 Jira Tool

5 actions available:

#### `jira.create_ticket`
Create a new Jira issue.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `summary` | string | Yes | Ticket title |
| `issue_type` | string | Yes | Issue type (Epic, Story, Task, Bug) |
| `project_key` | string | No | Project key (defaults to `JIRA_PROJECT_KEY` env var) |
| `description` | string | No | Ticket description |
| `assignee` | string | No | Assignee account ID |
| `labels` | array | No | List of labels |
| `priority` | string | No | Priority name (Highest, High, Medium, Low, Lowest) |

**Response:** `{ "key": "INS-101", "id": "10042", "self": "https://..." }`

#### `jira.update_ticket`
Update fields on an existing Jira issue.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticket_key` | string | Yes | Ticket key (e.g., "INS-101") |
| `fields` | object | Yes | Fields to update (e.g., `{"status": "In Progress"}`) |

**Response:** `{ "ticket_key": "INS-101", "updated": true }`

#### `jira.get_ticket`
Fetch details of a Jira issue.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticket_key` | string | Yes | Ticket key (e.g., "INS-101") |

**Response:** `{ "key": "INS-101", "summary": "...", "status": "In Progress", "assignee": "...", "description": "..." }`

#### `jira.get_sprint`
Get active/future sprints for a board.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `board_id` | string | Yes | Jira board ID |

**Response:** `{ "sprints": [...] }`

#### `jira.search_tickets`
Search tickets using JQL.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `jql` | string | Yes | JQL query string |
| `max_results` | integer | No | Max results to return (default: 50) |

**Response:** `{ "total": 15, "issues": [...] }`

---

### 13.2 GitHub Tool

5 actions available:

#### `github.create_branch`
Create a new Git branch.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `branch_name` | string | Yes | Name of the new branch |
| `base_ref` | string | No | Base branch (default: "main") |

**Response:** `{ "branch": "feature/INS-101-claims", "sha": "abc123..." }`

#### `github.push_code`
Push a file to a branch (create or update).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | Yes | Path in the repo (e.g., "backend/routers/claims.py") |
| `content` | string | Yes | File content (will be base64-encoded) |
| `branch` | string | Yes | Target branch |
| `commit_message` | string | Yes | Commit message |
| `sha` | string | No | Existing file SHA (required for updates) |

**Response:** `{ "path": "backend/routers/claims.py", "sha": "def456...", "commit_sha": "ghi789..." }`

#### `github.create_pr`
Open a pull request.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | PR title |
| `head` | string | Yes | Source branch |
| `base` | string | Yes | Target branch |
| `body` | string | No | PR description |

**Response:** `{ "pr_number": 42, "url": "https://github.com/.../pull/42", "state": "open" }`

#### `github.get_pr_status`
Check the status of a pull request.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pr_number` | integer | Yes | PR number |

**Response:** `{ "pr_number": 42, "title": "...", "state": "open", "mergeable": true, "merged": false, "url": "..." }`

#### `github.list_branches`
List all branches in the repository.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| *(none)* | — | — | — |

**Response:** `{ "branches": [{"name": "main", "sha": "abc..."}, ...] }`

---

### 13.3 Slack Tool

2 actions available:

#### `slack.send_message`
Send a plain text message to a channel.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | Yes | Message text |
| `channel` | string | No | Channel ID (defaults to `SLACK_DEFAULT_CHANNEL`) |

**Response:** `{ "channel": "C0123456789", "ts": "1617000000.000100" }`

#### `slack.send_notification`
Send a rich notification with color bar and formatting.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Notification title |
| `text` | string | Yes | Notification body |
| `channel` | string | No | Channel ID |
| `color` | string | No | Sidebar color hex (default: "#36a64f" green) |

**Response:** `{ "channel": "C0123456789", "ts": "1617000000.000200" }`

---

### 13.4 Google Calendar Tool

2 actions available:

#### `calendar.get_events`
Fetch upcoming calendar events.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `max_results` | integer | No | Max events to return (default: 10) |
| `time_min` | string | No | Start time filter (ISO 8601) |

**Response:** `{ "events": [{"id": "...", "summary": "Sprint Review", "start": "...", "end": "...", "attendees": [...]}] }`

#### `calendar.create_event`
Create a new calendar event.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `summary` | string | Yes | Event title |
| `start` | string | Yes | Start datetime (ISO 8601) |
| `end` | string | Yes | End datetime (ISO 8601) |
| `description` | string | No | Event description |
| `attendees` | array | No | List of attendee email addresses |
| `timezone` | string | No | Timezone (default: "UTC") |

**Response:** `{ "id": "...", "summary": "Sprint Review", "html_link": "https://calendar.google.com/...", "start": "...", "end": "..." }`

---

## 14. Memory System

The memory system is a collection of markdown files in the `memory/` directory that serve as shared knowledge between agents.

### Memory Files

| File | Written By | Purpose |
|------|-----------|---------|
| `constitution.md` | System (manual) | Supreme rulebook — all agents validate against this |
| `requirements.md` | PM Agent | Prioritized requirements (MoSCoW) |
| `user_stories.md` | PM Agent | User stories in standard format |
| `architecture.md` | Tech Lead Agent | System design, API contracts, DB schema |
| `tasks.md` | Scrum Agent | Sprint backlog with tasks and story points |
| `test_cases.md` | QA Agent | Test cases with type, priority, linked requirements |
| `decisions.md` | All agents | Architecture Decision Records (ADRs) |
| `system_state.json` | State Manager | Persisted system state (auto-managed) |

### Memory Rules (from Constitution)

1. **Read before write** — Agents must read existing memory before generating output to avoid conflicts
2. **Append, don't overwrite** — New entries are appended; existing records are never deleted without orchestrator approval
3. **Timestamps required** — All memory entries include timestamps and author agent ID
4. **Structured format** — Each file follows a defined markdown template

### How Agents Use Memory

```python
# Inside any agent:
constitution = self.load_constitution()       # Read rulebook
requirements = self.read_memory("requirements.md")  # Read requirements
architecture = self.read_memory("architecture.md")  # Read architecture

# After generating output:
self.write_memory("requirements.md", updated_content)  # Update memory
```

---

## 15. Constitution & Governance

The `memory/constitution.md` file is the supreme rulebook. It contains 14 sections:

1. **Project Identity** — Name, stack, languages
2. **Folder Structure Rules** — Where files go, `__init__.py` requirements
3. **Naming Conventions** — Python (snake_case), TypeScript (camelCase/PascalCase), Database (snake_case plural)
4. **Git Rules** — Conventional commits (`feat(scope): message`), atomic commits, no secrets
5. **Branching Strategy** — `main` → `develop` → `feature/*`, `bugfix/*`, `hotfix/*`, `release/*`
6. **Pull Request Rules** — Jira ticket reference, descriptions, approvals, CI checks
7. **Testing Requirements** — Coverage targets (80% backend, 70% frontend, 95% critical), test types
8. **Code Standards** — PEP 8, type hints, max function length (50 lines), max file length (400 lines)
9. **API Standards** — RESTful, versioned (`/api/v1/`), RFC 7807 errors, OpenAPI docs
10. **Security Standards** — No PII in logs, env vars for secrets, JWT with short expiry
11. **DevOps Practices** — Docker, multi-stage builds, health checks, zero-downtime deploys
12. **Communication Protocols** — Structured JSON responses, tool call format, status reporting
13. **Agent Governance** — No hallucination, permission enforcement, decision logging, orchestrator-mediated communication
14. **Data Governance** — Encryption, retention, audit logs, GDPR/CCPA compliance

### How Governance Works

1. Every agent calls `load_constitution()` before processing
2. Every agent calls `validate_output()` before returning a response
3. Validation checks:
   - Required keys present (`agent_id`, `status`, `output`)
   - Tool calls are within the agent's permission set
   - Failed responses include error details
4. The orchestrator can reject non-compliant responses

---

## 16. State Management & Sessions

### System State

The `StateManager` persists all system state to `memory/system_state.json`. It is thread-safe (uses `threading.RLock`).

**State structure:**
```json
{
  "workflow": {
    "current_stage": "requirements",
    "stages_completed": [],
    "stage_criteria": { ... },
    "started_at": "2026-04-05T10:00:00",
    "updated_at": "2026-04-05T10:00:00"
  },
  "sessions": {
    "uuid-here": {
      "session_id": "uuid-here",
      "messages": [
        {
          "role": "user",
          "content": "Build claims module",
          "timestamp": "2026-04-05T10:01:00",
          "metadata": {}
        },
        {
          "role": "assistant",
          "content": "I'll design the claims API...",
          "timestamp": "2026-04-05T10:01:05",
          "metadata": {"agent_id": "dev_backend_agent"}
        }
      ],
      "active_agents": ["dev_backend_agent"],
      "created_at": "2026-04-05T10:01:00",
      "updated_at": "2026-04-05T10:01:05"
    }
  },
  "project_metadata": {},
  "updated_at": "2026-04-05T10:01:05"
}
```

### Session Continuity

To continue a conversation, include the `session_id` from a previous response:

```bash
# First message (new session)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Define requirements for claims module"}'
# Response includes: "session_id": "abc-123"

# Follow-up message (same session)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Now design the architecture for those requirements",
    "session_id": "abc-123"
  }'
```

The session preserves full message history, active agents, and timestamps.

---

## 17. Docker Deployment

### Development (docker-compose)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f orchestrator

# Stop services
docker-compose down
```

This starts:
- **orchestrator** on port 8000 (with `.env` loaded, `memory/` mounted)
- **postgres** on port 5432 (database: `insure_os`, user: `postgres`, password: `postgres`)

### Production Build

```bash
# Build the image
docker build -t insure-os:latest .

# Run standalone
docker run -p 8000:8000 --env-file .env insure-os:latest
```

The Dockerfile uses multi-stage builds:
1. **Builder stage** — installs Python dependencies
2. **Runtime stage** — copies only necessary packages, exposes port 8000, runs uvicorn

### Health Checks

The Docker container includes a health check that pings `GET /health` every 30 seconds.

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' <container-id>
```

---

## 18. End-to-End Walkthrough

Here's a complete walkthrough of building a "Claims Module" from scratch using the system.

### Step 1: Start the server

```bash
uvicorn orchestrator.main:app --reload
```

### Step 2: Define requirements (PM Agent)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "We need a claims management module. Policyholders should be able to submit claims with supporting documents, adjusters should review and approve/deny claims, and all parties should see real-time status updates."
  }'
```

The PM Agent will:
- Parse requirements into REQ-001, REQ-002, REQ-003
- Assign MoSCoW priorities
- Generate user stories (US-001, US-002, ...)
- Write to `memory/requirements.md` and `memory/user_stories.md`
- Create a Jira Epic

### Step 3: Design architecture (Tech Lead Agent)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Design the system architecture for claims management including API contracts and database schema"
  }'
```

The Tech Lead Agent will:
- Read requirements from memory
- Design component architecture (Claims Service, Document Service, Notification Service)
- Define API contracts (POST/GET/PUT /api/v1/claims, POST /api/v1/claims/{id}/documents)
- Design database schema (claims, claim_documents, claim_status_history tables)
- Record decisions in `memory/decisions.md`
- Write architecture to `memory/architecture.md`

### Step 4: Plan the sprint (Scrum Agent)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a sprint plan with tasks for the claims module"
  }'
```

The Scrum Agent will:
- Read user stories from memory
- Break each story into backend, frontend, and QA tasks
- Assign story points
- Write sprint backlog to `memory/tasks.md`
- Create Jira tickets for each task
- Send a Slack notification about the new sprint

### Step 5: Build the backend (Backend Dev Agent)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Implement the backend API for claims management"
  }'
```

The Backend Dev Agent will:
- Read architecture from memory
- Generate FastAPI code (routers, models, services)
- Create a feature branch (`feature/INS-101-claims-api`)
- Push code to GitHub
- Open a PR to `develop`
- Update Jira ticket to "In Review"

### Step 6: Build the frontend (Frontend Dev Agent)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create the frontend components for claims submission and tracking dashboard"
  }'
```

The Frontend Dev Agent will:
- Read architecture from memory
- Generate Next.js components (ClaimsForm, ClaimsList, ClaimDetail)
- Create API hooks with TanStack Query
- Create a feature branch, push code, open PR

### Step 7: Test (QA Agent)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Generate test cases and validate the claims module against requirements"
  }'
```

The QA Agent will:
- Read requirements and architecture from memory
- Generate API tests, acceptance tests, security tests
- Create pytest files
- Validate architecture covers all requirements
- Log any gaps as bugs in Jira
- Write test cases to `memory/test_cases.md`

### Step 8: Deploy (DevOps Agent)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create Docker setup and CI/CD pipeline for deployment"
  }'
```

The DevOps Agent will:
- Generate multi-stage Dockerfiles for backend and frontend
- Create docker-compose files (dev + prod)
- Generate GitHub Actions workflows (CI + Deploy)
- Create nginx reverse proxy config
- Push everything to GitHub

### Step 9: Check progress

```bash
# Check SDLC workflow state
curl http://localhost:8000/api/v1/workflow

# Ask for sprint status
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the sprint status?"}'

# Check specific ticket
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the status of ticket INS-101?"}'
```

---

## 19. Autonomous Pipeline

The most powerful feature of the system. One API call drives a requirement through the **entire SDLC** automatically.

### Starting a Pipeline

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "We need a claims management module where policyholders can submit insurance claims, upload supporting documents, and track the status of their claims in real-time"
  }'
```

### What Happens Autonomously

The pipeline chains 6 stages, each feeding output to the next:

```
Stage 1: PM Agent
  ├── Extracts requirements from your natural language input
  ├── Assigns MoSCoW priorities
  ├── Generates user stories
  ├── Writes memory/requirements.md + memory/user_stories.md
  └── Creates Jira Epic via MCP

Stage 2: Tech Lead Agent
  ├── Reads requirements from Stage 1
  ├── Designs system architecture (components, APIs, DB schema)
  ├── Records Architecture Decision Records
  ├── Writes memory/architecture.md + memory/decisions.md
  └── Creates feature branch for architecture

Stage 3: Scrum Master Agent
  ├── Reads user stories + architecture from Stages 1-2
  ├── Breaks stories into backend/frontend/QA tasks
  ├── Assigns story points
  ├── Creates Jira tickets for each task
  ├── Writes memory/tasks.md
  └── Sends sprint plan notification to Slack

Stage 4: Development (Backend + Frontend Agents)
  ├── For each Jira task ticket:
  │   ├── Creates feature branch: feature/{TICKET-ID}-{description}
  │   ├── Routes to Backend or Frontend dev based on task type
  │   ├── Generates code based on architecture
  │   ├── Pushes code to GitHub
  │   ├── Updates Jira: To Do → In Progress → Code Review
  │   └── Creates Pull Request
  └── Passes dev outputs to QA stage

Stage 5: QA Agent
  ├── For each completed dev ticket:
  │   ├── Generates test cases (API, acceptance, security)
  │   ├── Validates code against requirements
  │   ├── If PASS → moves ticket to Done
  │   └── If FAIL → creates Bug ticket, moves back to In Progress
  └── Writes test results to memory/test_cases.md

Stage 6: DevOps Agent
  ├── Collects all feature branches
  ├── Generates Docker configs + CI/CD pipelines
  ├── Merges to QA branch
  └── Deploys
```

### Checking Pipeline Status

```bash
# List all pipelines
curl http://localhost:8000/api/v1/pipeline

# Get detailed status of a specific pipeline
curl http://localhost:8000/api/v1/pipeline/{pipeline_id}
```

Response shows each stage's status, output, tool calls executed, and timing:

```json
{
  "pipeline_id": "15a1dcd6...",
  "status": "completed",
  "current_stage": "devops",
  "stages": [
    {"stage": "pm", "agent_id": "pm_agent", "status": "completed", "tool_calls_count": 1},
    {"stage": "techlead", "agent_id": "techlead_agent", "status": "completed", "tool_calls_count": 1},
    {"stage": "scrum", "agent_id": "scrum_agent", "status": "completed", "tool_calls_count": 5},
    {"stage": "development", "agent_id": "dev_be_agent", "status": "completed", "tool_calls_count": 8},
    {"stage": "qa", "agent_id": "qa_agent", "status": "completed", "tool_calls_count": 3},
    {"stage": "devops", "agent_id": "devops_agent", "status": "completed", "tool_calls_count": 2}
  ],
  "jira_tickets": ["AISDLC-1", "AISDLC-2", "AISDLC-3"],
  "human_interventions": []
}
```

### Pipeline Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Created but not started |
| `running` | Currently executing stages |
| `paused_for_human` | Blocked — awaiting human input |
| `completed` | All 6 stages finished successfully |
| `failed` | A stage failed after retries and human intervention was not provided |

---

## 20. Scheduler — Automated Slack Updates

The scheduler runs background tasks for automated notifications.

### Starting the Scheduler

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/start
```

### What It Does

| Job | Frequency | Action |
|-----|-----------|--------|
| **Daily Standup** | Every day at 5:00 PM (configurable) | Queries Jira for sprint progress, checks calendar for meetings, posts formatted summary to Slack |
| **Hourly Status Update** | Every 60 minutes | Queries Jira for tickets that changed status in the last hour, posts changes to Slack |
| **Pipeline Health Check** | Every 5 minutes | Checks for stuck pipeline stages (>30 min), sends alert to Slack if issues found |

### Standup Message Format (Slack)

```
Daily Standup — Sprint 1

Sprint Progress: 5/12 tickets done (42%)

Completed Today:
  - AISDLC-3: Claims API endpoints
  - AISDLC-5: Claims form component

In Progress:
  - AISDLC-7: Document upload service

Blocked:
  - AISDLC-9: Payment integration (waiting for gateway credentials)

Upcoming Meetings:
  - 3:00 PM: Sprint Review
  - 4:30 PM: Architecture Discussion
```

### Manual Triggers

```bash
# Trigger standup notification now
curl -X POST http://localhost:8000/api/v1/scheduler/standup

# Trigger status update now
curl -X POST http://localhost:8000/api/v1/scheduler/status-update

# Check scheduler status
curl http://localhost:8000/api/v1/scheduler

# Stop scheduler
curl -X POST http://localhost:8000/api/v1/scheduler/stop
```

---

## 21. Human Intervention & Escalation

The system pauses and asks for human input when it cannot proceed autonomously.

### When Does It Pause?

1. **Agent fails after 2 retries** — stage keeps failing, pipeline pauses
2. **Agent returns BLOCKED status** — agent explicitly requests guidance
3. **Conflicting requirements detected** — architecture doesn't match requirements
4. **Tool calls fail repeatedly** — external service issues

### How It Works

When the pipeline pauses, it stores the question and context:

```bash
# Check pipeline status — look for human_interventions
curl http://localhost:8000/api/v1/pipeline/{pipeline_id}
```

Response when paused:
```json
{
  "status": "paused_for_human",
  "current_stage": "development",
  "human_interventions": [
    {
      "stage": "development",
      "question": "GitHub branch creation failed: repository not found. Please verify GITHUB_OWNER and GITHUB_REPO in .env",
      "resolved": false
    }
  ]
}
```

### Resuming After Human Input

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/{pipeline_id}/resume \
  -H "Content-Type: application/json" \
  -d '{
    "human_response": "I have updated the .env with correct GitHub credentials. Please retry."
  }'
```

The pipeline resumes from the stage where it paused and continues through the remaining stages.

---

## 22. Troubleshooting

### Server won't start

```bash
# Check Python version (need 3.11+)
python --version

# Reinstall dependencies
pip install -e ".[dev]"

# Check for port conflicts
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows
```

### Import errors

```bash
# Verify all modules import cleanly
python -c "
from orchestrator.models import ChatRequest, ChatResponse
from orchestrator.router import AgentRouter
from agents.pm_agent import PMAgent
from mcp.mcp_server import MCPServer
print('All imports OK')
"
```

### Tool calls failing

- Check `.env` has the correct API credentials
- Verify network connectivity to external services
- Check the MCP permission matrix — agents can only use their allowed tools
- Review tool call format: `{"type": "tool_call", "tool": "service.action", "input": {...}}`

### State issues

```bash
# Reset system state
rm memory/system_state.json
# Restart the server — fresh state will be created
```

### Memory file conflicts

- Memory files are append-only by default
- If a file is corrupted, agents will get an empty string from `read_memory()`
- You can safely reset any memory file to its template (see `memory/` directory)

---

## 23. API Reference

### Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Shallow health check |
| `GET` | `/ready` | Deep readiness check (agents, tools, scheduler, pipelines) |
| `POST` | `/api/v1/chat` | Send a message, get single-agent response |
| `WS` | `/ws/chat` | WebSocket for real-time chat |
| `GET` | `/api/v1/agents` | List all registered agents with permissions |
| `GET` | `/api/v1/workflow` | Get current SDLC workflow state |
| `POST` | `/api/v1/workflow/advance` | Advance SDLC to next stage |
| `POST` | `/api/v1/workflow/complete-criterion` | Mark an exit criterion as done |
| `POST` | `/api/v1/pipeline/start` | Start autonomous SDLC pipeline |
| `GET` | `/api/v1/pipeline` | List all pipeline runs |
| `GET` | `/api/v1/pipeline/{id}` | Get detailed pipeline status |
| `POST` | `/api/v1/pipeline/{id}/resume` | Resume paused pipeline with human input |
| `POST` | `/api/v1/scheduler/start` | Start background scheduler |
| `POST` | `/api/v1/scheduler/stop` | Stop background scheduler |
| `GET` | `/api/v1/scheduler` | Get scheduler status and job timings |
| `POST` | `/api/v1/scheduler/standup` | Trigger manual daily standup notification |
| `POST` | `/api/v1/scheduler/status-update` | Trigger manual hourly status update |
| `POST` | `/api/v1/tools/execute` | Execute a tool call directly via MCP |

### Enums

**SDLCStage:** `requirements`, `architecture`, `task_planning`, `development`, `testing`, `deployment`

**AgentStatus:** `in_progress`, `completed`, `failed`, `blocked`

**IntentType:** `requirements`, `architecture`, `task_planning`, `dev_backend`, `dev_frontend`, `qa`, `devops`, `general`

### Agent IDs

| ID | Role |
|----|------|
| `pm_agent` | Product Manager |
| `techlead_agent` | Tech Lead |
| `scrum_agent` | Scrum Master |
| `dev_be_agent` | Backend Developer |
| `dev_fe_agent` | Frontend Developer |
| `qa_agent` | QA Engineer |
| `devops_agent` | DevOps Engineer |

---

*Last updated: 2026-04-05*
*Version: 1.0.0*
