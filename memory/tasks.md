# Sprint Tasks — Auto Insurance Policy Management Module

> Author: Scrum Agent | Phase: TASKS | Date: 2026-04-06

---

## Sprint Objective
Deliver the auto insurance policy management module: quote generation with risk-based premium calculation, policy purchase, and policy document download.

---

## Task Breakdown

### Backend Tasks

| ID | Title | Linked Story | Priority | SP | Status | Depends On |
|----|-------|-------------|----------|-----|--------|------------|
| TASK-BE-001 | Create DB models and migrations (quotes, policies, audit_logs) | US-001, US-003 | High | 3 | To Do | — |
| TASK-BE-002 | Implement Pydantic request/response schemas | US-001, US-003 | High | 2 | To Do | — |
| TASK-BE-003 | Implement premium calculation engine with configurable risk rules | US-001, US-002 | High | 5 | To Do | TASK-BE-002 |
| TASK-BE-004 | Implement POST /api/v1/quotes endpoint (quote generation) | US-001 | High | 3 | To Do | TASK-BE-001, TASK-BE-003 |
| TASK-BE-005 | Implement GET /api/v1/quotes and GET /api/v1/quotes/{id} endpoints | US-005, US-002 | Medium | 2 | To Do | TASK-BE-001 |
| TASK-BE-006 | Implement POST /api/v1/policies endpoint (policy purchase) with mock payment | US-003 | High | 3 | To Do | TASK-BE-001, TASK-BE-002 |
| TASK-BE-007 | Implement GET /api/v1/policies and GET /api/v1/policies/{id} endpoints | US-006 | Medium | 2 | To Do | TASK-BE-001 |
| TASK-BE-008 | Implement GET /api/v1/policies/{id}/document (PDF generation) | US-004 | High | 5 | To Do | TASK-BE-006 |
| TASK-BE-009 | Add audit logging middleware for state-changing operations | NFR-003 | Medium | 2 | To Do | TASK-BE-001 |
| TASK-BE-010 | Add JWT auth dependency and ownership enforcement | NFR-001 | High | 2 | To Do | — |

### Frontend Tasks

| ID | Title | Linked Story | Priority | SP | Status | Depends On |
|----|-------|-------------|----------|-----|--------|------------|
| TASK-FE-001 | Set up Next.js project structure, API client, and TypeScript types | All | High | 3 | To Do | — |
| TASK-FE-002 | Build quote generation form (vehicle + driver inputs) | US-001 | High | 5 | To Do | TASK-FE-001 |
| TASK-FE-003 | Build quote result page with premium breakdown display | US-001, US-002 | High | 3 | To Do | TASK-FE-002 |
| TASK-FE-004 | Build quotes list page with status and pagination | US-005 | Medium | 2 | To Do | TASK-FE-001 |
| TASK-FE-005 | Build policy purchase flow (confirmation + payment mock) | US-003 | High | 3 | To Do | TASK-FE-003 |
| TASK-FE-006 | Build policies list page with status and pagination | US-006 | Medium | 2 | To Do | TASK-FE-001 |
| TASK-FE-007 | Build policy detail page with document download button | US-004, US-006 | High | 3 | To Do | TASK-FE-006 |

### QA Tasks

| ID | Title | Linked Story | Priority | SP | Status | Depends On |
|----|-------|-------------|----------|-----|--------|------------|
| TASK-QA-001 | Design test cases for quote generation and premium calculation | US-001, US-002 | High | 3 | To Do | — |
| TASK-QA-002 | Design test cases for policy purchase flow | US-003 | High | 2 | To Do | — |
| TASK-QA-003 | Design test cases for policy document download | US-004 | High | 2 | To Do | — |
| TASK-QA-004 | Design test cases for listing endpoints (quotes, policies) | US-005, US-006 | Medium | 1 | To Do | — |
| TASK-QA-005 | Execute API integration tests | All | High | 3 | To Do | TASK-BE-004 thru TASK-BE-008 |
| TASK-QA-006 | Execute E2E acceptance tests | All | High | 3 | To Do | TASK-FE-002 thru TASK-FE-007 |
| TASK-QA-007 | Validate security controls (auth, ownership, input sanitization) | NFR-001 | High | 2 | To Do | TASK-BE-010 |

---

## Critical Path

```
TASK-BE-001 (DB models)
  -> TASK-BE-003 (premium engine) -> TASK-BE-004 (quote endpoint)
  -> TASK-BE-006 (policy purchase) -> TASK-BE-008 (PDF generation)
  -> TASK-QA-005 (integration tests) -> TASK-QA-006 (E2E tests)
```

Frontend work can proceed in parallel once TASK-FE-001 is complete, but integration testing requires backend endpoints to be available.

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Premium engine complexity delays backend | Medium | Engine is self-contained; can be developed and tested in isolation |
| PDF generation library setup issues | Low | ReportLab is well-documented; fallback to simple text PDF if blocked |
| Frontend-backend contract drift | Medium | Schemas defined upfront; use OpenAPI spec as source of truth |

---

## Capacity and Sprint Scope

- **Backend**: 10 tasks, ~29 SP
- **Frontend**: 7 tasks, ~21 SP
- **QA**: 7 tasks, ~16 SP
- **Total**: 24 tasks, ~66 SP
- All Must Have stories are covered. Should Have stories (US-005, US-006) are included but can be deprioritized if capacity is constrained.

---

## Traceability

| User Story | Backend Tasks | Frontend Tasks | QA Tasks |
|------------|--------------|----------------|----------|
| US-001 | TASK-BE-001, BE-002, BE-003, BE-004 | TASK-FE-002, FE-003 | TASK-QA-001, QA-005 |
| US-002 | TASK-BE-003 | TASK-FE-003 | TASK-QA-001 |
| US-003 | TASK-BE-001, BE-002, BE-006 | TASK-FE-005 | TASK-QA-002, QA-005 |
| US-004 | TASK-BE-008 | TASK-FE-007 | TASK-QA-003 |
| US-005 | TASK-BE-005 | TASK-FE-004 | TASK-QA-004 |
| US-006 | TASK-BE-007 | TASK-FE-006 | TASK-QA-004 |

---

## V2 — Policy List Module Tasks (with Jira Ticket IDs)

### User Stories (Jira)

| Jira ID | Story | Priority | Status |
|---------|-------|----------|--------|
| AISDLC-16 | [US-007] View All Policies Table (Admin/Agent) | High | To Do |
| AISDLC-17 | [US-008] Cancel a Policy | High | To Do |
| AISDLC-18 | [US-009] Renew a Policy | High | To Do |
| AISDLC-19 | [US-010] Reinstate a Cancelled Policy | High | To Do |

### Implementation Tasks (Jira)

| Jira ID | Task | Type | Linked Stories | SP | Status |
|---------|------|------|---------------|-----|--------|
| AISDLC-20 | Add policy lifecycle columns + PolicyStatus.reinstated | BE | US-007 thru US-010 | 3 | To Do |
| AISDLC-21 | Implement admin policies router (list/cancel/renew/reinstate) | BE | US-007 thru US-010 | 5 | To Do |
| AISDLC-22 | Build admin policy list page with lifecycle actions UI | FE | US-007 thru US-010 | 5 | To Do |
| AISDLC-23 | Test admin policy list and lifecycle flows | QA | US-007 thru US-010 | 3 | To Do |

### Critical Path
```
AISDLC-20 (model changes) -> AISDLC-21 (admin router) -> AISDLC-22 (FE page) -> AISDLC-23 (QA tests)
```

### Slack Notification
- Sprint kickoff message posted to channel C0AQUM8NLNR with all ticket IDs and statuses.

---

## V3 — User-Facing Policy Renewal Tasks

### Sprint Objective (V3)
Deliver user-facing policy renewal: expiry notifications, premium recalculation preview, one-click renewal, and renewal chain navigation.

### Backend Tasks (V3)

| ID | Title | Linked Story | Priority | SP | Status | Depends On |
|----|-------|-------------|----------|-----|--------|------------|
| TASK-BE-V3-001 | Add renewal_premium_breakdown_json column to Policy model | US-012, US-013 | High | 1 | To Do | — |
| TASK-BE-V3-002 | Implement GET /api/v1/policies/expiring endpoint | US-011 | High | 2 | To Do | — |
| TASK-BE-V3-003 | Implement GET /api/v1/policies/{id}/renewal-preview endpoint with premium recalculation | US-012 | High | 3 | To Do | TASK-BE-V3-001 |
| TASK-BE-V3-004 | Implement POST /api/v1/policies/{id}/renew (user self-service) with premium recalculation and single-renewal guard | US-013 | High | 3 | To Do | TASK-BE-V3-001, TASK-BE-V3-003 |
| TASK-BE-V3-005 | Add Pydantic schemas for renewal preview/response including renewedFromPolicyId and renewedToPolicyId | US-012, US-014 | High | 2 | To Do | — |
| TASK-BE-V3-006 | Enhance GET /api/v1/policies/{id} to include renewedToPolicyId in response | US-014 | Medium | 1 | To Do | TASK-BE-V3-004 |
| TASK-BE-V3-007 | Add audit logging for renewal actions (old premium, new premium, policy refs) | NFR-006 | High | 1 | To Do | TASK-BE-V3-004 |

### Frontend Tasks (V3)

| ID | Title | Linked Story | Priority | SP | Status | Depends On |
|----|-------|-------------|----------|-----|--------|------------|
| TASK-FE-V3-001 | Add API client functions (getExpiringPolicies, getRenewalPreview, renewMyPolicy) and TypeScript types | All V3 | High | 2 | To Do | — |
| TASK-FE-V3-002 | Build ExpiryBanner component and integrate into policies list page | US-011 | High | 2 | To Do | TASK-FE-V3-001 |
| TASK-FE-V3-003 | Build renewal preview page (/policies/[id]/renew) with old vs new premium comparison | US-012 | High | 3 | To Do | TASK-FE-V3-001 |
| TASK-FE-V3-004 | Add "Renew This Policy" button to policy detail page with state-based visibility | US-013 | High | 2 | To Do | TASK-FE-V3-001 |
| TASK-FE-V3-005 | Add renewal chain links (Renewed from / Renewed as) to policy detail page | US-014 | Medium | 2 | To Do | TASK-FE-V3-001 |

### QA Tasks (V3)

| ID | Title | Linked Story | Priority | SP | Status | Depends On |
|----|-------|-------------|----------|-----|--------|------------|
| TASK-QA-V3-001 | Design test cases for expiry notification endpoint and UI | US-011 | High | 2 | To Do | — |
| TASK-QA-V3-002 | Design test cases for renewal preview and premium recalculation | US-012 | High | 2 | To Do | — |
| TASK-QA-V3-003 | Design test cases for one-click renewal (happy path, guards, idempotency) | US-013 | High | 2 | To Do | — |
| TASK-QA-V3-004 | Design test cases for renewal chain navigation | US-014 | Medium | 1 | To Do | — |
| TASK-QA-V3-005 | Execute API integration tests for all V3 endpoints | All V3 | High | 3 | To Do | TASK-BE-V3-004 |
| TASK-QA-V3-006 | Execute security tests (ownership, auth, cancelled policy guards) | NFR-001 | High | 2 | To Do | TASK-BE-V3-004 |

### Critical Path (V3)
```
TASK-BE-V3-001 (model change)
  -> TASK-BE-V3-003 (renewal preview) -> TASK-BE-V3-004 (renewal endpoint)
  -> TASK-BE-V3-006 (detail enhancement) + TASK-BE-V3-007 (audit)
  -> TASK-QA-V3-005 (integration tests) -> TASK-QA-V3-006 (security tests)
```

Frontend work (TASK-FE-V3-001 through V3-005) can proceed in parallel once API contracts are defined.

### Capacity (V3)
- **Backend**: 7 tasks, ~13 SP
- **Frontend**: 5 tasks, ~11 SP
- **QA**: 6 tasks, ~12 SP
- **Total**: 18 tasks, ~36 SP

### Traceability (V3)

| User Story | Backend Tasks | Frontend Tasks | QA Tasks |
|------------|--------------|----------------|----------|
| US-011 | TASK-BE-V3-002 | TASK-FE-V3-002 | TASK-QA-V3-001 |
| US-012 | TASK-BE-V3-001, V3-003, V3-005 | TASK-FE-V3-003 | TASK-QA-V3-002 |
| US-013 | TASK-BE-V3-004, V3-007 | TASK-FE-V3-004 | TASK-QA-V3-003 |
| US-014 | TASK-BE-V3-005, V3-006 | TASK-FE-V3-005 | TASK-QA-V3-004 |

---

## V4 — Configurable Risk Rules Engine Tasks

### Sprint Objective (V4)
Deliver admin-configurable risk rules engine: DB-stored rules with CRUD API, dynamic enable/disable, refactored premium engine, and admin UI.

### Backend Tasks (V4)

| ID | Title | Linked Story | Priority | SP | Status | Depends On |
|----|-------|-------------|----------|-----|--------|------------|
| TASK-BE-V4-001 | Create RiskRule model, seed default rules on startup | US-015, US-017 | High | 3 | To Do | — |
| TASK-BE-V4-002 | Create Pydantic schemas for risk rule CRUD | US-015 | High | 2 | To Do | — |
| TASK-BE-V4-003 | Implement admin risk rules router (list, create, update, delete, toggle) | US-015, US-016 | High | 5 | To Do | TASK-BE-V4-001, V4-002 |
| TASK-BE-V4-004 | Refactor premium_engine.py to load rules from DB | US-017 | High | 5 | To Do | TASK-BE-V4-001 |
| TASK-BE-V4-005 | Add audit logging for rule CRUD and toggle actions | NFR-008 | High | 2 | To Do | TASK-BE-V4-003 |

### Frontend Tasks (V4)

| ID | Title | Linked Story | Priority | SP | Status | Depends On |
|----|-------|-------------|----------|-----|--------|------------|
| TASK-FE-V4-001 | Add TypeScript types and API client for risk rules | All V4 | High | 2 | To Do | — |
| TASK-FE-V4-002 | Build admin risk rules list page with toggle/delete actions | US-018 | High | 3 | To Do | TASK-FE-V4-001 |
| TASK-FE-V4-003 | Build risk rule create/edit form with dynamic brackets editor | US-015, US-018 | High | 4 | To Do | TASK-FE-V4-001 |

### QA Tasks (V4)

| ID | Title | Linked Story | Priority | SP | Status | Depends On |
|----|-------|-------------|----------|-----|--------|------------|
| TASK-QA-V4-001 | Design test cases for risk rule CRUD and toggle | US-015, US-016 | High | 2 | To Do | — |
| TASK-QA-V4-002 | Design test cases for refactored premium engine with DB rules | US-017 | High | 3 | To Do | — |
| TASK-QA-V4-003 | Execute API integration tests for V4 endpoints | All V4 | High | 3 | To Do | TASK-BE-V4-003, V4-004 |
| TASK-QA-V4-004 | Execute regression tests for existing premium calculations | US-017 | High | 2 | To Do | TASK-BE-V4-004 |

### Critical Path (V4)
```
TASK-BE-V4-001 (model + seed)
  -> TASK-BE-V4-003 (CRUD router) + TASK-BE-V4-004 (engine refactor)
  -> TASK-BE-V4-005 (audit)
  -> TASK-QA-V4-003 (integration tests) -> TASK-QA-V4-004 (regression tests)
```

### Capacity (V4)
- **Backend**: 5 tasks, ~17 SP
- **Frontend**: 3 tasks, ~9 SP
- **QA**: 4 tasks, ~10 SP
- **Total**: 12 tasks, ~36 SP

### Traceability (V4)

| User Story | Backend Tasks | Frontend Tasks | QA Tasks |
|------------|--------------|----------------|----------|
| US-015 | TASK-BE-V4-001, V4-002, V4-003 | TASK-FE-V4-002, V4-003 | TASK-QA-V4-001 |
| US-016 | TASK-BE-V4-003, V4-005 | TASK-FE-V4-002 | TASK-QA-V4-001 |
| US-017 | TASK-BE-V4-001, V4-004 | — | TASK-QA-V4-002, V4-003, V4-004 |
| US-018 | — | TASK-FE-V4-001, V4-002, V4-003 | — |

---

*Last updated: 2026-04-09 | Author: Scrum Agent*
