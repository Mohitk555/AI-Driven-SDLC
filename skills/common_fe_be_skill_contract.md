# Common FE/BE Skill Contract

## Purpose
Provide a reusable, deterministic skill contract that frontend and backend agents can use for shared delivery behaviors without duplicating process logic.

This contract is intentionally standalone and not auto-bound to any agent. Agents may opt in later.

---

## Skill Metadata
- `skill_id`: `SKILL-COMMON-FEBE-001`
- `skill_name`: `common_delivery_execution`
- `version`: `1.0.0`
- `scope`: `DEVELOPMENT`
- `eligible_agents`: `dev_fe_agent`, `dev_be_agent`

---

## Invocation Contract

### Required Inputs
- `phase`: must be `DEVELOPMENT`
- `ticket_id`: Jira key (e.g., `AISDLC-123`)
- `task_id`: internal task reference (e.g., `TASK-BE-004`, `TASK-FE-002`)
- `work_type`: `feature` or `bugfix`
- `branch_base`: source branch for branch creation
- `implementation_summary`: concise scope statement
- `acceptance_checks`: list of checks to validate before handoff

### Optional Inputs
- `pr_id` (if existing)
- `related_ticket_ids`
- `risk_notes`
- `rollback_notes`

---

## Execution Steps (Deterministic)
1. Validate inputs and confirm task-to-ticket traceability.
2. Transition Jira ticket to `In Progress`.
3. Create GitHub branch name from policy:
   - `feature/<ticket-id>` when `work_type=feature`
   - `bugfix/<ticket-id>` when `work_type=bugfix`
4. Perform scoped implementation aligned to `implementation_summary`.
5. Run defined `acceptance_checks` and capture results.
6. Push code and create/update pull request.
7. Transition Jira ticket to `QA Testing` after checks pass.
8. Record all outcomes in `memory/plan.md` action log.

---

## Mandatory Tool Actions
- Jira:
  - status transition to `In Progress`
  - status transition to `QA Testing`
- GitHub:
  - branch create
  - push code and create/update PR

If a mandatory tool action fails:
- Retry up to 2 times for transient issues.
- If still failing, ask human:
  - "Tool actions failed after retries. Should I proceed to mark this phase as blocked?"
- Only mark blocked after explicit human confirmation.

---

## Validation Checklist
- Ticket/task linkage is explicit (`ticket_id` <-> `task_id`).
- Branch naming policy is correctly applied.
- Code changes are scoped to assigned task only.
- Acceptance checks are executed and recorded.
- Jira states reflect actual progress.
- PR/push evidence is present.
- Plan log includes tool attempts, retries, and outcomes.

---

## Output Schema
Each invocation result should return:
- `skill_id`
- `status`: `completed` | `failed` | `blocked`
- `objective`
- `artifacts_updated`
- `validations_performed`
- `tool_actions_taken`
- `blockers_human_input_required`

---

## Example Invocation (Template)
```json
{
  "phase": "DEVELOPMENT",
  "ticket_id": "AISDLC-220",
  "task_id": "TASK-FE-008",
  "work_type": "feature",
  "branch_base": "qa",
  "implementation_summary": "Add renewal confirmation UI with one-click action",
  "acceptance_checks": [
    "UI state transitions validated",
    "API contract alignment validated",
    "Error/empty/loading states validated"
  ]
}
```

---

## Notes
- This file defines a shared contract only.
- It does not modify orchestration or agent behavior until explicitly referenced by agent instructions.
