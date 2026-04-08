# System Architecture — Auto Insurance Policy Management Module

> Author: Tech Lead Agent | Phase: ARCHITECTURE | Date: 2026-04-06

---

## 1. Tech Stack (per Constitution)

- **Frontend**: Next.js 14 + TypeScript 5 + TailwindCSS
- **Backend**: FastAPI + Python 3.11+ + SQLAlchemy 2.0
- **Database**: PostgreSQL 16 (SQLite for local dev per ADR-001)
- **PDF Generation**: ReportLab
- **Auth**: JWT (access 15min, refresh 7d) — existing auth module, consumed not built
- **Validation**: Pydantic v2 (backend), Zod (frontend)

---

## 2. Module Boundaries

This module is scoped to the `policy` bounded context within InsureOS:

```
/backend
  /app
    /api/v1
      /quotes        — Quote endpoints
      /policies      — Policy endpoints
    /models          — SQLAlchemy ORM models
    /schemas         — Pydantic request/response schemas
    /services        — Business logic layer
      quote_service.py
      policy_service.py
      premium_engine.py
      document_service.py
    /core            — Config, deps, security utilities
    main.py          — FastAPI app entry point
  /migrations        — Alembic migrations
  /tests             — Mirrors source structure

/frontend
  /src
    /app
      /quotes        — Quote pages (list, create, detail)
      /policies      — Policy pages (list, detail)
    /components
      /quotes        — Quote-specific components
      /policies      — Policy-specific components
      /shared        — Shared UI components
    /lib
      /api           — API client functions
      /types         — TypeScript interfaces
      /utils         — Utility functions
```

---

## 3. API Contracts

Base path: `/api/v1`

### 3.1 Quotes

#### POST /api/v1/quotes — Generate Quote
**Request Body:**
```json
{
  "vehicle": {
    "make": "string",
    "model": "string",
    "year": 2024,
    "vin": "string",
    "mileage": 25000
  },
  "driver": {
    "firstName": "string",
    "lastName": "string",
    "dateOfBirth": "1990-01-15",
    "licenseNumber": "string",
    "address": {
      "street": "string",
      "city": "string",
      "state": "string",
      "zipCode": "string"
    },
    "drivingHistory": {
      "accidentCount": 0,
      "violationCount": 0,
      "yearsLicensed": 10
    }
  },
  "coverageType": "basic | full"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "premiumAmount": 1200.00,
  "coverageType": "basic",
  "status": "pending",
  "premiumBreakdown": [
    { "factor": "Base Rate", "value": "N/A", "impact": 800.00 },
    { "factor": "Driver Age", "value": "34", "impact": -50.00 },
    { "factor": "Violation Count", "value": "0", "impact": 0.00 },
    { "factor": "Vehicle Age", "value": "2 years", "impact": 50.00 },
    { "factor": "Coverage Level", "value": "basic", "impact": 400.00 }
  ],
  "vehicle": { "...": "..." },
  "driver": { "...": "..." },
  "expiresAt": "2026-05-06T00:00:00Z",
  "createdAt": "2026-04-06T00:00:00Z"
}
```

**Error 422:** RFC 7807 Problem Details with field-level errors.

#### GET /api/v1/quotes — List User's Quotes
**Query Params:** `page`, `pageSize` (default 20)
**Response 200:** Paginated array of quote summaries.

#### GET /api/v1/quotes/{id} — Get Quote Detail
**Response 200:** Full quote with premium breakdown.

### 3.2 Policies

#### POST /api/v1/policies — Purchase Policy from Quote
**Request Body:**
```json
{
  "quoteId": "uuid"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "policyNumber": "POL-20260406-A1B2C",
  "quoteId": "uuid",
  "status": "active",
  "coverageType": "basic",
  "premiumAmount": 1200.00,
  "effectiveDate": "2026-04-06",
  "expirationDate": "2027-04-06",
  "vehicle": { "...": "..." },
  "driver": { "...": "..." },
  "createdAt": "2026-04-06T00:00:00Z"
}
```

**Error 409:** Quote already purchased (idempotency guard).
**Error 410:** Quote expired.
**Error 402:** Payment failed.

#### GET /api/v1/policies — List User's Policies
**Query Params:** `page`, `pageSize`
**Response 200:** Paginated array of policy summaries.

#### GET /api/v1/policies/{id} — Get Policy Detail
**Response 200:** Full policy object.

#### GET /api/v1/policies/{id}/document — Download Policy PDF
**Response 200:** `application/pdf` binary stream.
**Error 403:** Not the policy owner.

---

## 4. Database Schema

### Table: `quotes`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK DEFAULT gen_random_uuid() |
| user_id | UUID | FK -> users(id), NOT NULL |
| vehicle_make | VARCHAR(100) | NOT NULL |
| vehicle_model | VARCHAR(100) | NOT NULL |
| vehicle_year | INTEGER | NOT NULL |
| vehicle_vin | VARCHAR(17) | NOT NULL |
| vehicle_mileage | INTEGER | NOT NULL |
| driver_first_name | VARCHAR(100) | NOT NULL |
| driver_last_name | VARCHAR(100) | NOT NULL |
| driver_date_of_birth | DATE | NOT NULL |
| driver_license_number | VARCHAR(50) | NOT NULL |
| driver_address_json | JSONB | NOT NULL |
| driver_accident_count | INTEGER | NOT NULL DEFAULT 0 |
| driver_violation_count | INTEGER | NOT NULL DEFAULT 0 |
| driver_years_licensed | INTEGER | NOT NULL DEFAULT 0 |
| coverage_type | VARCHAR(20) | NOT NULL CHECK (coverage_type IN ('basic', 'full')) |
| premium_amount | NUMERIC(10,2) | NOT NULL |
| premium_breakdown_json | JSONB | NOT NULL |
| status | VARCHAR(20) | NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'purchased', 'expired')) |
| expires_at | TIMESTAMPTZ | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes:** `idx_quotes_user_id`, `idx_quotes_status`, `idx_quotes_created_at`

### Table: `policies`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK DEFAULT gen_random_uuid() |
| policy_number | VARCHAR(20) | UNIQUE, NOT NULL |
| user_id | UUID | FK -> users(id), NOT NULL |
| quote_id | UUID | FK -> quotes(id), UNIQUE, NOT NULL |
| coverage_type | VARCHAR(20) | NOT NULL |
| premium_amount | NUMERIC(10,2) | NOT NULL |
| status | VARCHAR(20) | NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'cancelled')) |
| effective_date | DATE | NOT NULL |
| expiration_date | DATE | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes:** `idx_policies_user_id`, `idx_policies_policy_number`, `idx_policies_status`

### Table: `audit_logs`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK DEFAULT gen_random_uuid() |
| entity_type | VARCHAR(50) | NOT NULL |
| entity_id | UUID | NOT NULL |
| action | VARCHAR(50) | NOT NULL |
| actor_id | UUID | NOT NULL |
| details_json | JSONB | |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes:** `idx_audit_logs_entity`, `idx_audit_logs_actor_id`

---

## 5. Premium Calculation Engine

The risk engine (`premium_engine.py`) applies a configurable rule pipeline:

```
Base Rate = $800.00 (basic) or $1,500.00 (full)

Adjustments (additive):
  - Driver Age Factor:
      < 25 years: +$200
      25-65 years: -$50
      > 65 years: +$100
  - Violation Factor:
      0 violations: $0
      1 violation: +$150
      2+ violations: +$350
  - Accident Factor:
      0 accidents: $0
      1 accident: +$200
      2+ accidents: +$450
  - Vehicle Age Factor:
      < 3 years: +$100
      3-7 years: $0
      > 7 years: +$75
  - Mileage Factor:
      < 10,000: -$50
      10,000-30,000: $0
      > 30,000: +$100

Final Premium = max(Base Rate + sum(adjustments), $300.00)  // floor
```

Rules are defined as configuration data, not hardcoded logic. The engine reads rule definitions and applies them via a strategy pattern, making them auditable and extensible.

---

## 6. Cross-Cutting Concerns

### Authentication & Authorization
- All endpoints require valid JWT in Authorization header.
- User ID extracted from JWT claims.
- Policy/quote ownership enforced at service layer.

### Error Handling
- All errors follow RFC 7807 Problem Details.
- Validation errors return 422 with field-level detail.
- Business rule violations return appropriate 4xx codes.

### Observability
- Structured logging (JSON) at INFO/WARN/ERROR levels.
- Request correlation IDs via middleware.
- Health endpoint: `GET /health` and `GET /ready`.

### Audit Logging
- All state-changing operations log to `audit_logs` table.
- Risk rule evaluations logged with input factors and result.

---

---

## V2 — Policy List Module with Lifecycle Actions

### 3.3 Admin Policy List & Lifecycle Endpoints

#### GET /api/v1/admin/policies — List All Policies (Admin)
**Query Params:** `page`, `pageSize`, `status` (filter), `search` (policy number or customer name)
**Auth:** Admin role required.
**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "policyNumber": "POL-20260406-A1B2C",
      "customerName": "John Doe",
      "vehicleSummary": "2024 Toyota Camry",
      "coverageType": "basic",
      "premiumAmount": 850.00,
      "status": "active",
      "effectiveDate": "2026-04-06",
      "expirationDate": "2027-04-06"
    }
  ],
  "total": 100,
  "page": 1,
  "pageSize": 20
}
```

#### POST /api/v1/admin/policies/{id}/cancel — Cancel Policy
**Auth:** Admin role required.
**Request Body:**
```json
{ "reason": "Customer requested cancellation" }
```
**Response 200:** Updated policy object with status "cancelled".
**Error 400:** Policy not in active/reinstated state.

#### POST /api/v1/admin/policies/{id}/renew — Renew Policy
**Auth:** Admin role required.
**Response 201:** New policy object with new policy number and dates.
**Error 400:** Policy in cancelled state (must reinstate first).

#### POST /api/v1/admin/policies/{id}/reinstate — Reinstate Policy
**Auth:** Admin role required.
**Request Body:**
```json
{ "reason": "Customer paid overdue premium" }
```
**Response 200:** Updated policy object with status "reinstated".
**Error 400:** Policy not in cancelled state.

### Database Schema Changes

#### Table: `policies` — Updated
Add columns:
| Column | Type | Constraints |
|--------|------|-------------|
| renewed_from_policy_id | INTEGER | FK -> policies(id), NULLABLE |
| cancellation_reason | TEXT | NULLABLE |
| cancellation_date | TIMESTAMPTZ | NULLABLE |
| reinstatement_reason | TEXT | NULLABLE |
| reinstatement_date | TIMESTAMPTZ | NULLABLE |

Update status CHECK: `('active', 'expired', 'cancelled', 'reinstated')`

Add index: `idx_policies_renewed_from`

### Frontend: Admin Policy List Page
New page at `/admin/policies` with:
- Table component with columns: Policy #, Customer, Vehicle, Coverage, Premium, Status, Effective, Expiration, Actions
- Action dropdown per row: Cancel, Renew, Reinstate (conditionally enabled based on status)
- Filter bar: status dropdown, search input
- Modal dialogs for cancel/reinstate (reason input required)
- Pagination controls

---

## V3 — User-Facing Policy Renewal System

### 3.4 User Renewal Endpoints

#### GET /api/v1/policies/expiring — List User's Expiring Policies
**Auth:** Authenticated user (JWT).
**Description:** Returns the current user's policies expiring within 30 days (active/reinstated only).
**Response 200:**
```json
{
  "items": [
    {
      "id": 5,
      "policyNumber": "POL-20260406-A1B2C",
      "coverageType": "basic",
      "premiumAmount": 850.00,
      "expirationDate": "2027-04-06",
      "daysUntilExpiry": 12
    }
  ]
}
```

#### GET /api/v1/policies/{id}/renewal-preview — Preview Renewal Premium
**Auth:** Authenticated user, must own the policy.
**Description:** Recalculates the renewal premium using the original quote's vehicle/driver data with updated driver age at current date. Returns comparison of old vs new premium.
**Response 200:**
```json
{
  "policyId": 5,
  "policyNumber": "POL-20260406-A1B2C",
  "currentPremium": 850.00,
  "renewalPremium": 800.00,
  "premiumDifference": -50.00,
  "premiumBreakdown": [
    { "factor": "base_rate", "value": "basic", "impact": 800.00 },
    { "factor": "driver_age", "value": "35 (25-65)", "impact": -50.00 },
    { "factor": "violations", "value": "0", "impact": 0.00 },
    { "factor": "accidents", "value": "0", "impact": 0.00 },
    { "factor": "vehicle_age", "value": "3yr (3-7)", "impact": 0.00 },
    { "factor": "mileage", "value": "25000 (10k-30k)", "impact": 0.00 }
  ],
  "coverageType": "basic",
  "effectiveDate": "2026-04-08",
  "expirationDate": "2027-04-08"
}
```
**Error 400:** Policy is cancelled (must reinstate first).
**Error 400:** Policy already renewed (link to renewed policy provided).
**Error 403:** Not the policy owner.
**Error 404:** Policy not found.

#### POST /api/v1/policies/{id}/renew — Renew Policy (User Self-Service)
**Auth:** Authenticated user, must own the policy.
**Description:** Creates a new policy with recalculated premium. Policy must be active, expired, or reinstated. Returns the new policy.
**Response 201:**
```json
{
  "id": 12,
  "policyNumber": "POL-20260408-X9Y8Z",
  "quoteId": 3,
  "status": "active",
  "coverageType": "basic",
  "premiumAmount": 800.00,
  "effectiveDate": "2026-04-08",
  "expirationDate": "2027-04-08",
  "renewedFromPolicyId": 5,
  "createdAt": "2026-04-08T12:00:00Z"
}
```
**Error 400:** Policy is cancelled.
**Error 409:** Policy already renewed.
**Error 403:** Not the policy owner.

#### GET /api/v1/policies/{id} — Get Policy Detail (Updated)
**Description:** Existing endpoint enhanced with renewal chain fields.
**Response additions:**
```json
{
  "...existing fields...",
  "renewedFromPolicyId": 3,
  "renewedToPolicyId": 12
}
```

### Database Schema Changes (V3)

#### Table: `policies` — Updated
Add column:
| Column | Type | Constraints |
|--------|------|-------------|
| renewal_premium_breakdown_json | JSONB | NULLABLE |

The existing `renewed_from_policy_id` column (from V2) is sufficient for forward linking. Reverse linking (`renewed_to_policy_id`) is computed via query: `SELECT id FROM policies WHERE renewed_from_policy_id = :this_policy_id`.

No new tables required. The `audit_logs` table is reused for renewal audit entries.

### Premium Recalculation Strategy

On renewal, the system:
1. Loads the original policy's linked quote (vehicle/driver data).
2. Calls `premium_engine.calculate_premium()` with the same inputs but driver DOB evaluated at the current date (driver is now older).
3. Stores the new premium breakdown in `renewal_premium_breakdown_json` on the new policy.
4. Logs the old premium, new premium, and factor differences in the audit log.

### Frontend Architecture (V3)

New/modified pages:
- `/policies` (list) — Add expiry notification banner component at the top when expiring policies exist
- `/policies/[id]` (detail) — Add renewal chain links ("Renewed from" / "Renewed as"), expiry warning, and "Renew This Policy" button
- `/policies/[id]/renew` (new page) — Renewal preview page showing old vs new premium, breakdown, and "Confirm Renewal" button
- Shared components: `ExpiryBanner.tsx`, `RenewalPreview.tsx`

New API client functions:
- `getExpiringPolicies()` — GET /api/v1/policies/expiring
- `getRenewalPreview(id)` — GET /api/v1/policies/{id}/renewal-preview
- `renewMyPolicy(id)` — POST /api/v1/policies/{id}/renew

---

## V4 — Configurable Risk Rules Engine

### 3.5 Admin Risk Rules Endpoints

#### GET /api/v1/admin/risk-rules — List All Risk Rules
**Auth:** Admin role required.
**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "factorName": "driver_age",
      "label": "Driver Age",
      "isEnabled": true,
      "brackets": [
        { "condition": "< 25", "adjustment": 200.0 },
        { "condition": "25-65", "adjustment": -50.0 },
        { "condition": "> 65", "adjustment": 100.0 }
      ],
      "createdAt": "2026-04-09T00:00:00Z",
      "updatedAt": "2026-04-09T00:00:00Z"
    }
  ]
}
```

#### POST /api/v1/admin/risk-rules — Create Risk Rule
**Auth:** Admin role required.
**Request Body:**
```json
{
  "factorName": "credit_score",
  "label": "Credit Score",
  "brackets": [
    { "condition": "< 600", "adjustment": 300.0 },
    { "condition": "600-750", "adjustment": 0.0 },
    { "condition": "> 750", "adjustment": -100.0 }
  ]
}
```
**Response 201:** Created rule object.
**Error 409:** Duplicate factor_name.
**Error 422:** Validation error (empty brackets, missing fields).

#### PUT /api/v1/admin/risk-rules/{id} — Update Risk Rule
**Auth:** Admin role required.
**Request Body:** Same shape as create (partial updates allowed for label and brackets).
**Response 200:** Updated rule object.

#### DELETE /api/v1/admin/risk-rules/{id} — Soft-Delete Risk Rule
**Auth:** Admin role required.
**Response 200:** `{ "message": "Rule deleted", "id": 1 }`
**Error 404:** Rule not found.

#### PATCH /api/v1/admin/risk-rules/{id}/toggle — Enable/Disable Rule
**Auth:** Admin role required.
**Response 200:** Updated rule object with new `isEnabled` state.

### Database Schema (V4)

#### Table: `risk_rules`

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK AUTOINCREMENT |
| factor_name | VARCHAR(50) | UNIQUE, NOT NULL |
| label | VARCHAR(100) | NOT NULL |
| is_enabled | BOOLEAN | NOT NULL DEFAULT true |
| brackets_json | JSONB | NOT NULL |
| is_deleted | BOOLEAN | NOT NULL DEFAULT false |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes:** `idx_risk_rules_factor_name`, `idx_risk_rules_is_enabled`

`brackets_json` stores an ordered array of bracket objects:
```json
[
  { "condition": "< 25", "adjustment": 200.0 },
  { "condition": "25-65", "adjustment": -50.0 },
  { "condition": "> 65", "adjustment": 100.0 }
]
```

### Premium Engine Refactor Strategy

1. **Seed default rules**: On startup, if `risk_rules` table is empty, seed the 5 existing hardcoded rules (driver_age, violations, accidents, vehicle_age, mileage) with their current bracket definitions.
2. **Load rules at calculation time**: `calculate_premium()` queries `risk_rules` where `is_enabled=True AND is_deleted=False`, then applies each rule's brackets to the input data.
3. **Bracket evaluation**: Each rule's `factor_name` maps to an input field (e.g., `driver_age` -> computed from DOB, `violations` -> violation_count). The engine evaluates which bracket matches the input value and applies the corresponding adjustment.
4. **Backwards compatibility**: The function signature remains unchanged. The engine falls back to hardcoded logic if no DB rules are found (safety net for migration).
5. **Custom rules**: New rules added by admins specify a `factor_name` that maps to a quote input field. The engine dynamically maps factor names to input values via a registry dict.

### Frontend Architecture (V4)

New pages:
- `/admin/risk-rules` — List page with table of all rules, toggle switches, edit/delete actions
- `/admin/risk-rules/new` — Create form with factor name, label, dynamic brackets editor
- `/admin/risk-rules/[id]/edit` — Edit form pre-populated with existing rule data

New API client functions:
- `getRiskRules()` — GET /api/v1/admin/risk-rules
- `createRiskRule(data)` — POST /api/v1/admin/risk-rules
- `updateRiskRule(id, data)` — PUT /api/v1/admin/risk-rules/{id}
- `deleteRiskRule(id)` — DELETE /api/v1/admin/risk-rules/{id}
- `toggleRiskRule(id)` — PATCH /api/v1/admin/risk-rules/{id}/toggle

---

## 7. Traceability Matrix

| Requirement | Architecture Component |
|-------------|----------------------|
| REQ-001 | POST /api/v1/quotes, QuoteService, quote form UI |
| REQ-002 | PremiumEngine, premium_breakdown in quote response |
| REQ-003 | POST /api/v1/policies, PolicyService, policies table |
| REQ-004 | GET /api/v1/policies/{id}/document, DocumentService, ReportLab |
| REQ-005 | GET /api/v1/quotes, quotes list page |
| REQ-006 | GET /api/v1/policies, policies list page |
| REQ-007 | GET /api/v1/admin/policies, Admin policies list page |
| REQ-008 | POST /api/v1/admin/policies/{id}/cancel, cancel logic, audit_logs |
| REQ-009 | POST /api/v1/admin/policies/{id}/renew, renewal logic, new policy creation |
| REQ-010 | POST /api/v1/admin/policies/{id}/reinstate, reinstate logic, audit_logs |
| NFR-001 | JWT middleware, ownership checks, admin role enforcement |
| NFR-002 | Performance targets in service layer, pagination |
| NFR-003 | audit_logs table, risk evaluation logging |
| NFR-004 | Data retention policy, encryption at rest |
| REQ-011 | GET /api/v1/policies/expiring, ExpiryBanner component |
| REQ-012 | GET /api/v1/policies/{id}/renewal-preview, premium_engine recalculation, RenewalPreview component |
| REQ-013 | POST /api/v1/policies/{id}/renew, user ownership check, new policy creation |
| REQ-014 | GET /api/v1/policies/{id} (enhanced), renewal chain links in policy detail page |
| NFR-005 | Performance targets for renewal recalculation and creation |
| NFR-006 | audit_logs entries for all renewal actions with premium comparison |

| REQ-015 | CRUD endpoints for risk_rules, risk_rules table, admin risk-rules pages |
| REQ-016 | PATCH /api/v1/admin/risk-rules/{id}/toggle, is_enabled column, audit_logs |
| REQ-017 | Refactored premium_engine.py, risk_rules DB query, bracket evaluation |
| REQ-018 | /admin/risk-rules list page, toggle/edit/delete UI |
| NFR-007 | Performance targets for DB-loaded rule engine |
| NFR-008 | audit_logs entries for all rule CRUD and toggle actions |

---

*Last updated: 2026-04-09 | Author: Tech Lead Agent*
