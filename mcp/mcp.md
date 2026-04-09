# MCP Tooling Instruction Contract

## Purpose
Define deterministic tool usage rules for Jira, GitHub, Slack, and Calendar without Python orchestration code outside `backend/`.

## Allowed Tool Domains
- `jira.*` for ticketing, sprint planning, and status checks
- `github.*` for branches, file updates, commits, and PR workflows
- `slack.*` for notifications and channel updates
- `calendar.*` for schedule planning and milestone alignment

## Invocation Contract
Every tool call request must include:
1. `tool`
2. `intent`
3. `input`
4. `expected_output`

Every tool result must include:
1. `success`
2. `data`
3. `error`
4. `timestamp`

## Reliability Rules
- Never fabricate tool output.
- On tool failure, retry up to 2 times for transient errors.
- Persist all outcomes in `memory/plan.md` update log.
- Escalate to human after retries to confirm whether phase should be marked `blocked`.
- Only mark `blocked` after explicit human confirmation.
- For phases with mandatory tool actions, do not return success for phase completion if required calls are missing.

## Security Rules
- Load credentials only from environment variables.
- Never write secrets to memory artifacts or chat output.
- Redact token-like values in logs.

## Phase Guardrails and Mandatory Actions
- REQUIREMENTS:
	- Allowed: `jira.*`, `slack.*`
	- Mandatory: none by default unless requirement intake explicitly asks external tracking updates.
- ARCHITECTURE:
	- Allowed: `jira.*`, `github.*`
	- Mandatory: none by default.
- TASKS:
	- Allowed: `jira.*`, `slack.*`, `calendar.*`
	- Mandatory: at least one Jira create/update action for BE/FE/QA ticket set and one Slack status post.
- DEVELOPMENT:
	- Allowed: `github.*`, `jira.*`
	- Mandatory: Jira status transition and GitHub branch/code action (branch create, push, or PR update).
- TESTING:
	- Allowed: `jira.*`, `github.*`, `slack.*`
	- Mandatory: Jira test outcome action (defect create/status update) and Slack QA summary post.
- DEPLOYMENT:
	- Allowed: `github.*`, `calendar.*`, `slack.*`
	- Mandatory: GitHub merge/release action and Slack deployment update.

Phase completion must be rejected when mandatory actions are missing or unsuccessful.