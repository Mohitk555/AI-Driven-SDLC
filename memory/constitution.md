# Constitution — AI Engineering OS for Insurance Platform

> This is the supreme rulebook. ALL agents MUST load and validate against this document before generating any output.

---

## 1. Project Identity

- **Name**: Insurance Operating System (InsureOS)
- **Stack**: Next.js (frontend) + FastAPI (backend) + PostgreSQL (database)
- **Language**: Python 3.11+ (backend/agents), TypeScript 5+ (frontend)

---

## 2. Folder Structure Rules

```
/project-root
  /orchestrator        — Central brain: routing, state, workflow
  /agents              — AI agent implementations (one file per agent)
  /mcp                 — Model Context Protocol server and tool adapters
    /tools             — Individual tool integrations (Jira, GitHub, etc.)
  /memory              — Shared knowledge base (markdown files)
  /frontend            — Next.js application
  /backend             — FastAPI application
  /docs                — Documentation and ADRs
```

### Rules:
- No code files in the project root (only config files).
- Each module must have an `__init__.py`.
- Tests live in a `/tests` directory mirroring the source structure.
- Static assets go in `/frontend/public`.
- Database migrations go in `/backend/migrations`.

---

## 3. Naming Conventions

### Python
- **Files**: `snake_case.py` (e.g., `pm_agent.py`)
- **Classes**: `PascalCase` (e.g., `PMAgent`)
- **Functions/Methods**: `snake_case` (e.g., `create_requirement`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- **Private members**: prefix with `_` (e.g., `_internal_state`)

### TypeScript
- **Files**: `kebab-case.tsx` for components, `camelCase.ts` for utilities
- **Components**: `PascalCase` (e.g., `SprintBoard`)
- **Functions**: `camelCase` (e.g., `fetchTickets`)
- **Interfaces/Types**: `PascalCase` prefixed with `I` for interfaces (e.g., `ITicket`)

### Database
- **Tables**: `snake_case`, plural (e.g., `claims`, `policy_holders`)
- **Columns**: `snake_case` (e.g., `created_at`, `policy_number`)
- **Indexes**: `idx_{table}_{column}` (e.g., `idx_claims_status`)

---

## 4. Git Rules

### Commit Messages
Format: `<type>(<scope>): <description>`

Types:
- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation
- `refactor` — code restructuring
- `test` — adding/updating tests
- `chore` — maintenance tasks
- `ci` — CI/CD changes

Examples:
```
feat(claims): add claim submission endpoint
fix(auth): resolve token expiration bug
docs(api): update swagger descriptions
```

### Rules:
- Commit messages must be imperative mood ("add", not "added").
- Each commit must be atomic — one logical change per commit.
- Never commit secrets, credentials, or `.env` files.
- Never commit directly to `main` or `develop`.

---

## 5. Branching Strategy

```
main              — production-ready code
├── develop       — integration branch
│   ├── feature/* — new features (e.g., feature/INS-123-claims-module)
│   ├── bugfix/*  — bug fixes (e.g., bugfix/INS-456-login-error)
│   ├── hotfix/*  — urgent production fixes
│   └── release/* — release candidates
```

### Rules:
- Branch names: `<type>/<ticket-id>-<short-description>`
- All branches originate from `develop` (except hotfixes from `main`).
- Delete branches after merge.
- Rebase feature branches on `develop` before PR.

---

## 6. Pull Request Rules

- Every PR must reference a Jira ticket (e.g., `INS-123`).
- PR title format: `[INS-XXX] <description>`
- PR must include:
  - Description of changes
  - Testing steps
  - Screenshots (for UI changes)
- Minimum 1 approval required before merge.
- All CI checks must pass.
- No force pushes to shared branches.
- Squash merge to `develop`, merge commit to `main`.

---

## 7. Testing Requirements

### Coverage Targets:
- Backend: minimum 80% line coverage
- Frontend: minimum 70% line coverage
- Critical paths (auth, payments, claims): 95% coverage

### Test Types:
- **Unit tests**: Required for all business logic
- **Integration tests**: Required for API endpoints
- **E2E tests**: Required for critical user flows
- **Contract tests**: Required for inter-service APIs

### Rules:
- Tests must be independent and idempotent.
- Use fixtures/factories, not hardcoded data.
- Mock external services, never call real APIs in tests.
- Test file naming: `test_{module}.py` (Python), `{component}.test.tsx` (TypeScript)
- Every bug fix must include a regression test.

---

## 8. Code Standards

### Python (Backend/Agents):
- Follow PEP 8.
- Use type hints on all function signatures.
- Use Pydantic models for data validation.
- Use async/await for I/O operations.
- Maximum function length: 50 lines.
- Maximum file length: 400 lines.
- Use dependency injection over global state.

### TypeScript (Frontend):
- Strict mode enabled.
- Use functional components with hooks.
- Use Zod for runtime validation.
- Use TanStack Query for server state.
- No `any` type — use `unknown` and narrow.
- Components must be < 200 lines.

### General:
- No magic numbers — use named constants.
- No commented-out code in PRs.
- Handle errors explicitly — no bare `except` / `catch`.
- Log at appropriate levels (DEBUG, INFO, WARN, ERROR).

---

## 9. API Standards

- RESTful design with consistent naming.
- All endpoints versioned: `/api/v1/...`
- Request/response bodies use camelCase JSON keys.
- Pagination: `?page=1&pageSize=20`
- Errors follow RFC 7807 Problem Details format:
  ```json
  {
    "type": "validation_error",
    "title": "Invalid input",
    "status": 422,
    "detail": "Field 'email' is required",
    "instance": "/api/v1/users"
  }
  ```
- All endpoints must have OpenAPI documentation.

---

## 10. Security Standards

- Never log sensitive data (PII, tokens, passwords).
- Use environment variables for all secrets.
- Validate and sanitize all user input.
- Use parameterized queries — no string concatenation for SQL.
- JWT tokens with short expiry (15min access, 7d refresh).
- CORS configured per environment.
- Rate limiting on all public endpoints.

---

## 11. DevOps Practices

- All services containerized with Docker.
- Use multi-stage builds for production images.
- Health check endpoints required: `/health` and `/ready`
- Environment configs: `development`, `staging`, `production`.
- Infrastructure as Code (Terraform/Pulumi preferred).
- CI pipeline stages: lint → test → build → deploy.
- Zero-downtime deployments required.
- Rollback plan documented for every release.

---

## 12. Communication Protocols

### Agent-to-Orchestrator:
- Agents return structured JSON responses.
- Every response must include: `agent_id`, `status`, `output`, `tool_calls` (if any).

### Tool Calls:
```json
{
  "type": "tool_call",
  "tool": "<service>.<action>",
  "input": { ... }
}
```

### Status Updates:
- Agents must report: `in_progress`, `completed`, `failed`, `blocked`.
- Failed operations must include error details and suggested recovery.

### Memory Updates:
- Before writing, read current state to avoid overwrites.
- Append new entries; never delete existing records without orchestrator approval.
- All memory entries must include timestamps and author agent ID.

---

## 13. Agent Governance

- Agents must NOT hallucinate tool data — if data is unavailable, report it.
- Agents must NOT exceed their defined permissions.
- Agents must validate output against this constitution before returning.
- Agents must log all decisions in `decisions.md` with rationale.
- Cross-agent communication must go through the orchestrator — no direct agent-to-agent calls.

---

## 14. Data Governance

- All PII must be encrypted at rest and in transit.
- Data retention policies must be enforced.
- Audit logs required for all data mutations.
- GDPR/CCPA compliance required for user data.
- Insurance data must comply with relevant regulatory standards.

---

*Last updated: 2026-04-05*
*Version: 1.0.0*
