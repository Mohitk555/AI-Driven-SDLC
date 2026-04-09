# Architecture Decision Records — Auto Insurance Policy Management Module

> Updated by Tech Lead Agent | Date: 2026-04-06

---

## ADR-001: Use SQLite for Development, PostgreSQL for Production

**Date:** 2026-04-05
**Status:** Accepted
**Author:** Tech Lead Agent

**Decision:** Use SQLite as the database for local development and PostgreSQL for staging/production environments.

**Rationale:** SQLite requires zero setup for local development. SQLAlchemy ORM abstracts the database layer, so the same models and queries work with both. This gives developers a frictionless local experience while retaining PostgreSQL's robustness in production.

**Alternatives Considered:**
- PostgreSQL everywhere (via Docker) — adds setup complexity for local dev
- MySQL — less feature-rich than PostgreSQL for JSONB and advanced constraints

---

## ADR-002: JWT for Authentication (Consumed, Not Built)

**Date:** 2026-04-05
**Status:** Accepted
**Author:** Tech Lead Agent

**Decision:** Use JWT for user authentication. The auth module is assumed to exist; this module consumes JWT tokens for user identification and authorization.

**Rationale:** JWT is stateless and works naturally with decoupled frontend/backend. The policy module extracts user_id from JWT claims and enforces resource ownership.

**Alternatives Considered:**
- Session-based auth — requires server-side state, harder to scale

---

## ADR-003: Configurable Risk Rule Engine via Strategy Pattern

**Date:** 2026-04-06
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** Premium calculation requires applying multiple risk factors (driver age, violations, vehicle age, mileage, coverage level). Business rules may change frequently.

**Decision:** Implement the premium engine as a pipeline of configurable rule strategies. Each rule is a callable that receives quote input and returns a labeled adjustment. Rules are defined as configuration data, making them auditable, testable, and extensible without code changes.

**Alternatives Considered:**
- Hardcoded if/else logic — brittle, not auditable, violates separation of concerns
- External rules engine (e.g., Drools) — over-engineered for V1 scope
- Database-stored rules — adds complexity; config-based is sufficient for now with a clear migration path

**Consequences:**
- Adding new risk factors requires only adding a new rule configuration entry
- All rule evaluations are logged with factor inputs and impacts for compliance
- Performance is O(n) where n is the number of rules — negligible for <20 rules

---

## ADR-004: PDF Generation via ReportLab (Server-Side)

**Date:** 2026-04-06
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** Users need to download policy documents as PDFs (REQ-004). PDF must include policy details, vehicle/driver info, premium breakdown, and terms.

**Decision:** Use ReportLab for server-side PDF generation. PDFs are generated on-demand per request.

**Alternatives Considered:**
- WeasyPrint (HTML-to-PDF) — heavier dependency, slower for structured documents
- Client-side PDF generation — less secure, inconsistent rendering
- Pre-generated and cached PDFs — adds storage complexity; on-demand is sufficient for V1

**Consequences:**
- PDF generation adds ~1-3s per request (within NFR-002 5s target)
- If load increases, can add caching layer without API contract changes

---

## ADR-005: Mock Payment Interface

**Date:** 2026-04-06
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** Policy purchase requires payment (REQ-003). Actual payment gateway integration is out of scope for V1.

**Decision:** Implement a `PaymentService` interface with a mock implementation that always succeeds. The interface contract is defined so that a real gateway (Stripe, etc.) can be swapped in later via dependency injection.

**Alternatives Considered:**
- Skip payment entirely — loses the purchase flow validation
- Integrate Stripe now — out of scope, adds complexity and credentials management

**Consequences:**
- Purchase flow is fully testable end-to-end with mock
- Real payment integration is a single implementation swap

---

## ADR-006: Quote Expiration Policy (30 Days)

**Date:** 2026-04-06
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** Quotes should not remain valid indefinitely as risk factors and pricing may change.

**Decision:** Quotes expire 30 days after creation. Expired quotes cannot be purchased — user must generate a new quote.

**Alternatives Considered:**
- No expiration — risk of stale pricing
- 7-day expiration — too aggressive for insurance purchase decisions

---

## ADR-007: Idempotent Policy Purchase

**Date:** 2026-04-06
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** Users may double-click the purchase button or retry after network issues (US-003 edge case).

**Decision:** The `quote_id` column in `policies` has a UNIQUE constraint. Attempting to purchase an already-purchased quote returns 409 Conflict with the existing policy details. This provides natural idempotency without separate idempotency keys.

**Alternatives Considered:**
- Idempotency key header — more general but unnecessary for this one-to-one relationship
- Client-side debounce only — not reliable for network retries

---

## ADR-008: Policy Lifecycle State Machine (Cancel/Renew/Reinstate)

**Date:** 2026-04-06
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** The policy list module requires lifecycle actions: cancel, renew, reinstate. These transitions must be well-defined and auditable.

**Decision:** Implement a strict state machine for policy status:
- `active` -> can be cancelled or renewed
- `expired` -> can be renewed
- `cancelled` -> can be reinstated (then becomes `reinstated`)
- `reinstated` -> treated as active; can be cancelled or renewed

Renewal creates a NEW policy record (not an in-place update) with a `renewed_from_policy_id` FK reference. This preserves full history.

Cancel and reinstate are in-place status changes with mandatory reason fields and audit log entries.

**Alternatives Considered:**
- In-place status cycling without new records for renewal — loses history, complicates audit
- Soft-delete for cancellation — obscures state; explicit status is clearer
- Single "modify" endpoint — too generic, insufficient guardrails

**Consequences:**
- Clear, auditable state transitions
- Renewal history is fully traceable via `renewed_from_policy_id` chain
- Admin-only endpoints protect against unauthorized lifecycle changes

---

## ADR-009: Admin Role Enforcement for Policy Lifecycle

**Date:** 2026-04-06
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** Policy lifecycle actions (cancel, renew, reinstate) and the all-policies list are admin/agent operations, not end-user self-service.

**Decision:** All `/api/v1/admin/policies` endpoints require the `require_admin` dependency (existing in `backend/auth.py`). This leverages the existing `UserRole.ADMIN` enum and `require_admin` function.

**Alternatives Considered:**
- Fine-grained RBAC with separate agent/admin roles — over-engineered for V2
- No role check (any authenticated user) — violates least-privilege principle

---

## ADR-010: User Self-Service Renewal (Separate from Admin Renewal)

**Date:** 2026-04-08
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** V2 implemented admin-only renewal at `/api/v1/admin/policies/{id}/renew` which uses the same premium amount without recalculation. V3 requires user-facing renewal with premium recalculation.

**Decision:** Create a separate user-facing renewal endpoint at `POST /api/v1/policies/{id}/renew` that:
1. Enforces ownership (user can only renew their own policies).
2. Recalculates premium using the current risk engine with updated driver age.
3. Includes a preview endpoint (`GET /api/v1/policies/{id}/renewal-preview`) so users see the new premium before confirming.
4. Prevents double-renewal via DB query on `renewed_from_policy_id`.

The admin endpoint remains unchanged for backward compatibility.

**Alternatives Considered:**
- Reuse admin endpoint with role-based behavior — violates single responsibility, different business logic (recalculation vs same premium)
- Auto-renewal without confirmation — poor UX when premium changes; user must consent to new premium
- Renewal via new quote — over-complex; user shouldn't re-enter vehicle/driver data

**Consequences:**
- Two renewal paths: admin (same premium) and user (recalculated premium)
- Users are informed of premium changes before committing
- Clear audit trail distinguishes admin vs self-service renewals

---

## ADR-011: Single-Renewal Constraint per Policy

**Date:** 2026-04-08
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** Without constraints, a user could renew the same policy multiple times, creating parallel renewal branches and coverage confusion.

**Decision:** Each policy can be renewed exactly once. The system checks for an existing policy with `renewed_from_policy_id = current_policy_id` before allowing renewal. Only the latest policy in a renewal chain can be renewed further.

**Alternatives Considered:**
- Allow unlimited renewals of any policy — creates ambiguous renewal trees
- DB unique constraint on `renewed_from_policy_id` — too rigid; may conflict with admin renewal path

**Consequences:**
- Clean linear renewal chain: A -> B -> C
- Users are guided to renew only the most recent policy
- Query-time check rather than DB constraint (allows admin override if needed)

---

## ADR-012: Portal-Only Expiry Notifications (No Email/SMS in V3)

**Date:** 2026-04-08
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** REQ-011 requires expiry notifications. Email/SMS adds external service dependencies.

**Decision:** V3 implements portal-only notifications via a dedicated API endpoint (`GET /api/v1/policies/expiring`) that returns policies expiring within 30 days. The frontend renders these as banner alerts. Email/SMS can be added in a future iteration.

**Alternatives Considered:**
- Email notifications now — requires email service integration, template system, deliverability monitoring
- Background job with cron — adds infrastructure complexity for V3

**Consequences:**
- Simple, self-contained implementation
- Users must log in to see notifications (acceptable for V3)
- Clear migration path to email/push notifications later

---

## ADR-013: DB-Stored Risk Rules with Bracket Evaluation Model

**Date:** 2026-04-09
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** The premium engine currently uses hardcoded Python functions for each risk factor. The business needs to add, remove, and modify rules without code deployment.

**Decision:** Store risk rules in a `risk_rules` database table with a JSONB `brackets_json` column containing ordered bracket definitions. The engine loads enabled rules at calculation time and evaluates each against input values using a generic bracket matcher.

**Alternatives Considered:**
- External rules engine (Drools, OPA) — over-engineered for bracket-based math
- YAML/JSON config files — no admin UI, requires redeployment
- DSL-based rules with code execution — security risk, complexity

**Consequences:**
- Rules are fully admin-configurable without code changes
- Bracket evaluation is generic and auditable
- No arbitrary code execution — safe by design
- Slight DB query overhead (negligible for <20 rules)

---

## ADR-014: Soft-Delete for Risk Rules

**Date:** 2026-04-09
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** Deleting a risk rule must not corrupt historical premium breakdowns that referenced it.

**Decision:** Risk rules use soft-delete (`is_deleted = true`). Deleted rules are excluded from new calculations but remain in the database. Historical premium breakdowns store factor name and adjustment as snapshot data (in `premium_breakdown_json`), so they are self-contained.

**Alternatives Considered:**
- Hard delete with cascade — loses audit trail
- Archive to separate table — adds complexity

---

## ADR-015: Seed Default Rules on First Run

**Date:** 2026-04-09
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** The premium engine must remain backwards-compatible after the refactor. The 5 existing hardcoded rules must produce identical results when loaded from the database.

**Decision:** On application startup, if the `risk_rules` table is empty, seed the 5 default rules (driver_age, violations, accidents, vehicle_age, mileage) with bracket definitions that exactly match the current hardcoded logic. This ensures zero-disruption migration.

**Consequences:**
- Existing tests pass without modification after the refactor
- Admin can immediately modify or disable default rules
- Clear migration path from hardcoded to configurable

---

## ADR-016: Single Aggregation Endpoint for Claims Dashboard

**Date:** 2026-04-09
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** The dashboard needs total counts, status breakdowns, amounts, approval rates, and processing time. These could be separate endpoints or a single aggregated response.

**Decision:** Single endpoint `GET /api/v1/admin/claims/dashboard` returns all statistics in one response. The backend performs all aggregations in SQL (GROUP BY, AVG, JOIN) in a single optimized query set, avoiding N+1 patterns.

**Alternatives Considered:**
- Separate endpoints per stat — more HTTP round trips, harder to keep filters consistent
- Materialized view / pre-computed cache — over-engineered for current scale

**Consequences:**
- One API call populates the entire dashboard
- Filters (dateFrom, dateTo, claimType) apply uniformly
- As data grows, can add DB-level indexes or caching without API changes

---

## ADR-017: Processing Time from Status History Table

**Date:** 2026-04-09
**Status:** Accepted
**Author:** Tech Lead Agent

**Context:** Average processing time requires knowing when a claim was resolved. The `claims` table has `created_at` and `updated_at`, but `updated_at` could be overwritten by non-resolution changes.

**Decision:** Compute resolution time by joining `claim_status_history` and finding the first entry where `new_status IN ('approved','rejected')`. This gives the exact timestamp of the resolution decision, not just the last update.

**Alternatives Considered:**
- Use `claims.updated_at` — unreliable, overwritten by any subsequent update
- Add `resolved_at` column to claims — requires migration, duplicates data already in history

---

*Last updated: 2026-04-09 | Author: Tech Lead Agent*
