# Requirements — Auto Insurance Policy Management Module

> Author: PM Agent | Phase: REQUIREMENTS | Date: 2026-04-06

---

## Context Summary

Stakeholder requests a policy management module for auto insurance within InsureOS. The module must allow users to generate a quote based on vehicle and driver details, calculate premiums using predefined risk rules, purchase a policy, and download policy documents. This is a core revenue-generating capability aligned with the insurance platform's primary mission.

---

## Functional Requirements

### REQ-001: Quote Generation
- **Priority**: Must Have
- **Description**: The system shall allow users to generate an auto insurance quote by providing vehicle details (make, model, year, VIN, mileage) and driver details (name, date of birth, license number, driving history, address).
- **Acceptance Criteria**:
  - Given valid vehicle and driver inputs, when the user submits the quote form, then the system returns a premium estimate with coverage options.
  - Given incomplete or invalid inputs, when the user submits the form, then the system returns field-level validation errors per RFC 7807.

### REQ-002: Premium Calculation via Risk Rules
- **Priority**: Must Have
- **Description**: The system shall calculate the insurance premium using a predefined, configurable risk-rule engine that factors in driver age, driving history (accidents, violations), vehicle age, vehicle type, and coverage level.
- **Acceptance Criteria**:
  - Given a driver with zero violations and a vehicle under 5 years old, when basic coverage is selected, then the premium falls within the low-risk tier.
  - Given a driver with 2+ violations and a vehicle over 10 years old, when full coverage is selected, then the premium falls within the high-risk tier.
  - All risk rules and their weights must be auditable and traceable.

### REQ-003: Policy Purchase
- **Priority**: Must Have
- **Description**: The system shall allow users to purchase a policy from an approved quote. Upon purchase, the system creates a policy record with a unique policy number, effective dates, coverage details, and payment status.
- **Acceptance Criteria**:
  - Given an approved quote, when the user confirms purchase and payment succeeds, then a policy record is created with status "active" and a unique policy number is generated.
  - Given a payment failure, when the user attempts purchase, then the system returns an error without creating a policy and logs the failure.

### REQ-004: Policy Document Download
- **Priority**: Must Have
- **Description**: The system shall generate and allow users to download a PDF policy document containing policy number, coverage details, insured vehicle/driver information, premium breakdown, effective/expiration dates, and terms.
- **Acceptance Criteria**:
  - Given an active policy, when the user requests a document download, then the system generates and returns a PDF within 5 seconds.
  - The PDF must include all policy details as specified and be accessible only by the policy holder.

### REQ-005: Quote Listing and History
- **Priority**: Should Have
- **Description**: The system shall allow users to view their past quotes and their statuses (pending, purchased, expired).
- **Acceptance Criteria**:
  - Given an authenticated user, when they navigate to quotes list, then all their quotes are displayed with status, date, and summary.

### REQ-006: Policy Listing and Status
- **Priority**: Should Have
- **Description**: The system shall allow users to view their active and past policies with status (active, expired, cancelled).
- **Acceptance Criteria**:
  - Given an authenticated user, when they navigate to policies list, then all their policies are displayed with status, policy number, and coverage summary.

---

## Non-Functional Requirements

### NFR-001: Security
- All endpoints must require authentication (JWT).
- PII (driver details, address) must be encrypted at rest.
- Policy documents must be scoped to the owning user — no cross-user access.
- Input sanitization and parameterized queries mandatory.

### NFR-002: Performance
- Quote generation and premium calculation must complete within 2 seconds (p95).
- Policy document PDF generation must complete within 5 seconds (p95).
- API pagination for listing endpoints (default pageSize=20).

### NFR-003: Auditability
- All quote, purchase, and policy state changes must be audit-logged with actor, timestamp, and action.
- Risk rule evaluations must be logged for compliance traceability.

### NFR-004: Compliance
- Insurance data handling must comply with applicable regulatory standards.
- Data retention policies must be enforced for policy records.

---

## Assumptions
1. User authentication and authorization are handled by an existing auth module (out of scope for this module).
2. Payment processing is represented as a mock/stub interface — actual payment gateway integration is out of scope for this iteration.
3. Risk rules are business-defined and stored as configuration, not hardcoded.
4. PDF generation uses a server-side library (e.g., ReportLab or WeasyPrint).

## Out of Scope
- Claims management
- Policy renewal/modification workflows
- Agent/broker portal
- Real payment gateway integration
- Multi-vehicle policies (single vehicle per policy in V1)

## Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Risk rule complexity may grow beyond V1 scope | Medium | Keep rule engine configurable; use strategy pattern |
| PDF generation performance under load | Medium | Cache generated PDFs; async generation if needed |
| Regulatory compliance gaps | High | Flag for legal review before production deployment |

---

## V2 — Policy List Module with Lifecycle Actions

### REQ-007: Policy List View (Admin/Agent)
- **Priority**: Must Have
- **Description**: The system shall provide a tabular list view of all issued policies (not just the current user's), accessible to admin/agent users. The table shall display: policy number, customer name, vehicle summary, coverage type, premium amount, status (active/expired/cancelled/reinstated), effective date, and expiration date. The list shall support pagination, sorting, and search/filter by status, customer name, or policy number.
- **Acceptance Criteria**:
  - Given an admin user, when they navigate to the policy list page, then they see a paginated table of all policies with the specified columns.
  - Given the user applies a status filter (e.g., "active"), when the table refreshes, then only policies matching that status are displayed.
  - Given the user searches by policy number or customer name, when results load, then matching policies are shown.

### REQ-008: Cancel Policy
- **Priority**: Must Have
- **Description**: The system shall allow authorized users to cancel an active policy. Cancellation changes the policy status to "cancelled", records the cancellation reason and date, and creates an audit log entry.
- **Acceptance Criteria**:
  - Given an active policy, when an authorized user submits a cancellation with a reason, then the policy status changes to "cancelled" and an audit log is created.
  - Given a non-active policy (expired/cancelled), when cancellation is attempted, then the system rejects with an appropriate error.
  - Cancellation reason is mandatory.

### REQ-009: Renew Policy
- **Priority**: Must Have
- **Description**: The system shall allow authorized users to renew an active or expired policy. Renewal creates a new policy record linked to the original, with a new policy number, updated effective/expiration dates (12 months from renewal date), and the same coverage details. The original policy's status remains unchanged.
- **Acceptance Criteria**:
  - Given an active or expired policy, when an authorized user initiates renewal, then a new policy record is created with new dates and a new policy number.
  - Given a cancelled policy, when renewal is attempted, then the system rejects (must reinstate first).
  - The renewed policy references the original policy ID for traceability.

### REQ-010: Reinstate Policy
- **Priority**: Must Have
- **Description**: The system shall allow authorized users to reinstate a cancelled policy. Reinstatement changes the policy status to "reinstated" (treated as active), records the reinstatement reason and date, and creates an audit log entry.
- **Acceptance Criteria**:
  - Given a cancelled policy, when an authorized user submits reinstatement with a reason, then the policy status changes to "reinstated" and an audit log is created.
  - Given a non-cancelled policy, when reinstatement is attempted, then the system rejects with an appropriate error.
  - Reinstatement reason is mandatory.

---

## V3 — User-Facing Policy Renewal System

### REQ-011: Expiry Notification in User Portal
- **Priority**: Must Have
- **Description**: The system shall display a visible notification banner on the user's policy list and policy detail pages when any of their policies is within 30 days of expiration. The notification shall include the policy number, expiration date, and a direct link/button to initiate renewal.
- **Acceptance Criteria**:
  - Given an authenticated user with a policy expiring within 30 days, when they view the policies list or policy detail page, then a notification banner is displayed with policy number, days remaining, and a "Renew Now" action.
  - Given a user whose policies all expire more than 30 days from now, when they view the policies list, then no expiry notification is shown.
  - Given a cancelled policy expiring within 30 days, when the user views their policies, then no renewal notification is shown for that policy (cancelled policies are not renewable).

### REQ-012: Renewal Premium Recalculation
- **Priority**: Must Have
- **Description**: When a user initiates policy renewal, the system shall recalculate the renewal premium using the current risk-rule engine based on the original policy's vehicle and driver data, with updated driver age (computed at renewal time). The user shall see the new premium amount and breakdown before confirming renewal.
- **Acceptance Criteria**:
  - Given a user initiates renewal for an active/expired policy, when the system processes the renewal request, then the premium is recalculated using current risk rules with the driver's current age.
  - Given the recalculated premium differs from the original, when the user views the renewal preview, then both old and new premiums are displayed with the breakdown.
  - Risk rule evaluation for renewal must be logged for audit compliance.

### REQ-013: One-Click Renewal
- **Priority**: Must Have
- **Description**: The system shall allow authenticated users to renew their own active or expired policies with a single confirmation click from the policy detail page. Renewal creates a new policy record with a new policy number, new effective/expiration dates (12 months), recalculated premium, and a reference to the original policy. The original policy status remains unchanged.
- **Acceptance Criteria**:
  - Given an active or expired policy owned by the user, when the user clicks "Renew" and confirms, then a new policy is created with status "active", new dates, recalculated premium, and `renewed_from_policy_id` set.
  - Given a cancelled policy, when the user attempts to renew, then the system rejects with "Policy cannot be renewed — contact support".
  - Given a policy already renewed (a newer policy exists in the renewal chain), when the user attempts to renew the old policy, then the system rejects with "This policy has already been renewed".
  - Mock payment is assumed (consistent with existing V1 mock payment approach).

### REQ-014: View Renewed Policy Details
- **Priority**: Must Have
- **Description**: The system shall allow users to view the full details of their renewed policy, including: new policy number, new premium amount and breakdown, new effective/expiration dates, coverage details, and a link to the original (parent) policy. The original policy detail page shall also show a link to the renewed (child) policy.
- **Acceptance Criteria**:
  - Given a renewed policy, when the user views its detail page, then all policy details are shown including a "Renewed from" link to the parent policy.
  - Given a policy that has been renewed, when the user views the original policy detail page, then a "Renewed as" link to the new policy is displayed.
  - The renewal chain is navigable in both directions.

---

### Non-Functional Requirements (V3 Additions)

### NFR-005: Renewal Performance
- Renewal premium recalculation must complete within 2 seconds (p95).
- Renewal policy creation must complete within 3 seconds (p95) including premium recalculation and audit logging.

### NFR-006: Renewal Auditability
- All renewal actions (initiation, premium recalculation, policy creation) must be audit-logged with actor, timestamp, old premium, new premium, and policy references.

---

### Assumptions (V3)
1. Users can only renew their own policies (ownership enforcement via JWT).
2. Renewal uses the same vehicle and driver data from the original quote — users cannot modify vehicle/driver details during renewal (that requires a new quote).
3. Driver age is the only factor that changes at renewal time (recalculated from DOB).
4. A policy can only be renewed once — the most recent policy in a renewal chain is the only one eligible for further renewal.
5. Mock payment continues from V1.

### Out of Scope (V3)
- Email/SMS notifications for expiry (portal-only notifications).
- Modifying coverage type during renewal (must create new quote).
- Bulk renewal operations.
- Automatic renewal without user confirmation.

### Risks (V3)
| Risk | Impact | Mitigation |
|------|--------|------------|
| Premium change surprises users on renewal | Medium | Show old vs new premium comparison before confirmation |
| Renewal chain integrity with concurrent requests | Low | DB-level constraint on renewed_from_policy_id + idempotency check |
| Performance of premium recalculation at scale | Low | Engine is O(n) with <10 rules; negligible |

---

---

## V4 — Configurable Risk Rules Engine

### REQ-015: Admin Risk Rule CRUD
- **Priority**: Must Have
- **Description**: The system shall allow admin users to create, read, update, and delete risk rules via API and admin UI. Each risk rule defines a factor name, evaluation logic (bracket-based thresholds with associated adjustments), and a display label. Rules are stored in the database and loaded by the premium engine at calculation time.
- **Acceptance Criteria**:
  - Given an admin user, when they create a new risk rule with factor name, brackets, and label, then the rule is persisted and available for premium calculations.
  - Given an admin user, when they update an existing rule's brackets or label, then subsequent premium calculations use the updated values.
  - Given an admin user, when they delete a rule, then it is soft-deleted (marked inactive) and excluded from future calculations. Historical calculations remain unaffected.
  - Given a non-admin user, when they attempt any rule CRUD operation, then the system returns 403 Forbidden.

### REQ-016: Dynamic Rule Enable/Disable
- **Priority**: Must Have
- **Description**: The system shall allow admin users to enable or disable individual risk rules without deleting them. Disabled rules are skipped during premium calculation but remain in the database for re-enabling. The premium breakdown shall only include enabled rules.
- **Acceptance Criteria**:
  - Given an admin user, when they disable an active rule, then the rule's `is_enabled` flag is set to false and it is excluded from all subsequent premium calculations.
  - Given an admin user, when they re-enable a previously disabled rule, then it is included in future premium calculations.
  - Given a premium calculation is triggered, when the engine evaluates rules, then only enabled rules contribute to the premium breakdown.
  - Rule enable/disable actions must be audit-logged.

### REQ-017: Risk Score Influences Premium Calculation
- **Priority**: Must Have
- **Description**: The premium calculation engine shall be refactored to load enabled risk rules from the database at runtime instead of using hardcoded adjustment functions. Each rule defines brackets (condition ranges) and their corresponding premium adjustments. The engine applies all enabled rules to produce a risk score that determines the final premium.
- **Acceptance Criteria**:
  - Given the default set of risk rules (driver_age, violations, accidents, vehicle_age, mileage) are seeded as DB records, when a premium is calculated, then the result matches the current hardcoded engine output for the same inputs.
  - Given an admin adds a new custom rule (e.g., "credit_score"), when a premium is calculated, then the new rule's brackets are evaluated and its adjustment appears in the breakdown.
  - Given an admin disables the "violations" rule, when a premium is calculated for a driver with violations, then the violations factor shows $0 impact and does not affect the total.
  - The engine must remain backwards-compatible: existing quotes and policies retain their original premium breakdowns.

### REQ-018: Admin Risk Rules List View
- **Priority**: Must Have
- **Description**: The system shall provide an admin UI page listing all risk rules with their name, label, enabled/disabled status, number of brackets, and action buttons (edit, toggle enable/disable, delete). The list supports sorting and shows which rules are currently active in calculations.
- **Acceptance Criteria**:
  - Given an admin navigates to the risk rules page, when the page loads, then all rules are displayed with name, label, status (enabled/disabled), bracket count, and actions.
  - Given an admin clicks "Disable" on an enabled rule, when the action completes, then the rule shows as disabled without page reload.
  - Given an admin clicks "Edit" on a rule, when the edit form loads, then they can modify brackets and label and save changes.

---

### Non-Functional Requirements (V4 Additions)

### NFR-007: Rule Engine Performance
- Premium calculation with DB-loaded rules must complete within 2 seconds (p95), matching current hardcoded engine performance.
- Rule CRUD operations must complete within 1 second (p95).

### NFR-008: Rule Auditability
- All rule CRUD and enable/disable actions must be audit-logged with actor, timestamp, rule ID, and change details (before/after state for updates).

---

### Assumptions (V4)
1. Risk rules use a bracket-based evaluation model: each rule defines ordered brackets with conditions (e.g., "age < 25") and corresponding adjustment amounts.
2. The existing 5 hardcoded rules (driver_age, violations, accidents, vehicle_age, mileage) will be seeded as default DB records on first run.
3. Base rates by coverage type remain as application constants (not configurable via rules UI in V4).
4. Minimum premium floor ($300) remains as an application constant.
5. Custom rules added by admins use the same bracket evaluation model — no custom code execution.

### Out of Scope (V4)
- Rule versioning / history (audit log provides change trail).
- Rule scheduling (effective dates for rule changes).
- Complex rule dependencies (rules are independent and additive).
- Base rate configuration via UI.

### Risks (V4)
| Risk | Impact | Mitigation |
|------|--------|------------|
| DB-loaded rules slower than hardcoded | Low | Rules are few (<20); single query with caching option |
| Breaking existing premium calculations | High | Seed default rules matching current hardcoded logic; regression tests |
| Admin misconfiguration produces invalid premiums | Medium | Minimum premium floor enforced; preview before save |

---

## V5 — Claims Analytics Dashboard

### REQ-019: Claims Summary Statistics API
- **Priority**: Must Have
- **Description**: The system shall provide an admin API endpoint that returns aggregated claims statistics: total claims filed, count by status (submitted, under_review, approved, rejected, info_required), total and average claim amounts, and average processing time (from submitted to approved/rejected).
- **Acceptance Criteria**:
  - Given an admin user, when they call `GET /api/v1/admin/claims/dashboard`, then the response includes: totalClaims, countByStatus (object with each status count), totalAmount, averageAmount, and averageProcessingDays.
  - Given optional query parameters `dateFrom` and `dateTo`, when provided, then statistics are scoped to claims created within that date range.
  - Given an optional `claimType` filter, when provided, then statistics are scoped to that claim type only.
  - Given no claims exist, when the endpoint is called, then all counts are 0 and averages are null.
  - Given a non-admin user, when they call the endpoint, then the system returns 403 Forbidden.

### REQ-020: Approved vs Rejected Breakdown
- **Priority**: Must Have
- **Description**: The dashboard API shall include an approval/rejection breakdown: number of approved claims, number of rejected claims, approval rate (percentage), and rejection rate (percentage). This allows admins to monitor decision quality and claim processing trends.
- **Acceptance Criteria**:
  - Given there are 8 approved and 2 rejected claims, when the dashboard is called, then approvedCount=8, rejectedCount=2, approvalRate=80.0, rejectionRate=20.0.
  - Given no resolved claims (all still pending), when the dashboard is called, then approvalRate and rejectionRate are null (not 0).

### REQ-021: Average Claim Processing Time
- **Priority**: Must Have
- **Description**: The system shall compute the average time in days between claim submission (created_at) and resolution (the timestamp when status changed to approved or rejected, from `claim_status_history`). Only resolved claims are included in the calculation.
- **Acceptance Criteria**:
  - Given claims that were resolved at varying intervals, when the dashboard is called, then averageProcessingDays reflects the mean of (resolution_timestamp - created_at) in days, rounded to 1 decimal.
  - Given no resolved claims, when the dashboard is called, then averageProcessingDays is null.

### REQ-022: Claims Dashboard UI
- **Priority**: Must Have
- **Description**: The system shall provide an admin dashboard page displaying claims statistics as visual cards and a summary table. The page shows: total claims card, approved/rejected ratio card, average processing time card, and a status breakdown table. Optional date range and claim type filters are available.
- **Acceptance Criteria**:
  - Given an admin navigates to `/admin/claims-dashboard`, when the page loads, then they see stat cards for total claims, approval/rejection rates, average processing time, and a status breakdown.
  - Given the admin selects a date range or claim type filter, when the filter is applied, then all stats update accordingly.
  - Given no claims exist, when the page loads, then cards show "0" or "N/A" appropriately with an empty state message.

---

### Non-Functional Requirements (V5 Additions)

### NFR-009: Dashboard Performance
- The dashboard statistics endpoint must complete within 3 seconds (p95), even with 10,000+ claims.
- The frontend page must render within 2 seconds after data arrives.

---

### Assumptions (V5)
1. Processing time is computed from `claims.created_at` to the first `claim_status_history` entry where `new_status` is "approved" or "rejected".
2. Claims that are still pending (submitted, under_review, info_required) are excluded from processing time calculations.
3. The dashboard is admin-only; regular users do not have access.
4. Date filters use ISO date format (YYYY-MM-DD).

### Out of Scope (V5)
- Charts/graphs (card + table view only in V5; charting can be added in V6).
- Export to CSV/PDF.
- Real-time/WebSocket updates.
- Per-user claim analytics.

### Risks (V5)
| Risk | Impact | Mitigation |
|------|--------|------------|
| Aggregation query performance with large claim sets | Medium | Indexed columns (status, created_at, claim_type); single-query aggregation |
| Processing time accuracy with missing status history | Low | Fallback to null if no resolution entry exists |

---

## V6 — Admin Dashboard UI (Frontend-Only, Figma-Driven)

### REQ-023: Dashboard KPI Cards
- **Priority**: Must Have
- **Description**: The system shall display four KPI summary cards on the admin dashboard: Today's Sales (currency), Total Sales (currency), Total Orders (count), and Total Customers (count). Each card shows the metric value, a label, a percentage change indicator, and a sparkline/trend graph. Data is sourced from mock data (frontend-only).
- **Acceptance Criteria**:
  - Given the user navigates to the dashboard, when the page loads, then four KPI cards are displayed with metric label, value, percentage change, and trend sparkline.
  - Given the page is in loading state, when data is being fetched, then skeleton placeholders are shown for each card.
  - Given the page encounters an error, when data fetch fails, then an error state is displayed with retry option.

### REQ-024: General Sales Activity Chart
- **Priority**: Must Have
- **Description**: The system shall display a line/area chart showing general sales activity over time. The chart includes a date range filter and a "View Report" action link. Data is from mock data.
- **Acceptance Criteria**:
  - Given the dashboard loads, when the General Sale section renders, then a line/area chart is displayed with time on x-axis and sales amount on y-axis.
  - Given the user selects a date range filter, when the selection changes, then the chart data updates accordingly.
  - Given the user clicks "View Report", when the action triggers, then a report view action is initiated.

### REQ-025: Sales Analytics Bar Chart
- **Priority**: Must Have
- **Description**: The system shall display a bar chart showing sales analytics breakdown. The chart includes a date range filter. Data is from mock data.
- **Acceptance Criteria**:
  - Given the dashboard loads, when the Sales Analytics section renders, then a bar chart is displayed with categories and corresponding values.
  - Given the user selects a different date range, when the filter changes, then the bar chart updates.

### REQ-026: Recent Orders Table
- **Priority**: Must Have
- **Description**: The system shall display a recent orders table with columns: ID, Item, Quantity, Order Date, Amount, and Status. Status values include PAID, PENDING, and other order statuses. Each row has a "Details" action button. Data is from mock data.
- **Acceptance Criteria**:
  - Given the dashboard loads, when the Recent Orders section renders, then a table is displayed with columns ID, Item, Quantity, Order Date, Amount, Status, and a Details action.
  - Given an order has status PAID, when displayed, then a green/success badge is shown.
  - Given an order has status PENDING, when displayed, then a yellow/warning badge is shown.
  - Given no orders exist, when the table renders, then an empty state message is shown.

### REQ-027: Dashboard Layout and Navigation
- **Priority**: Must Have
- **Description**: The dashboard page shall follow the Figma design layout (1440px frame) with a left sidebar navigation (98px), top header with greeting, search bar, notification/language/avatar controls. The layout must be responsive and match the Figma screen's visual hierarchy.
- **Acceptance Criteria**:
  - Given the user navigates to the dashboard, when the page loads, then the layout matches the Figma reference: sidebar + header + KPI row + charts row + orders table.
  - Given the dashboard renders, when inspected, then spacing, typography hierarchy, and component states match the Figma design.

---

### Non-Functional Requirements (V6 Additions)

### NFR-010: Dashboard Rendering Performance
- The dashboard page must render within 1 second with mock data (no API dependency).
- All chart components must initialize within 500ms of data availability.

### NFR-011: UI State Coverage
- All dashboard sections must support loading, empty, error, and default states.
- State transitions must be smooth with appropriate skeleton/placeholder UI.

---

### Assumptions (V6)
1. This is a frontend-only implementation — no backend API dependency.
2. All data is provided via mock/static data within the frontend codebase.
3. Chart libraries (e.g., recharts or chart.js) may be added as dependencies.
4. The Figma design (file key: 7HuO8t9vziGBunYKOXPdWH, node: 3:7) is the authoritative visual reference.
5. The dashboard is accessible at `/admin/dashboard` route.

### Out of Scope (V6)
- Backend API integration (mock data only).
- Real-time data updates.
- Export/download functionality.
- Mobile-specific responsive breakpoints (desktop-first).

### Risks (V6)
| Risk | Impact | Mitigation |
|------|--------|------------|
| Chart library integration complexity | Low | Use well-supported library (recharts); fallback to simple SVG |
| Figma design parity gaps in implementation | Medium | Fetch Figma data via MCP; validate layout/spacing/typography post-implementation |

---

## Open Questions
- None blocking at this time.

---

## Traceability Seed
- REQ-001 through REQ-027 established.
- NFR-001 through NFR-011 established.
- All requirements will trace forward to user stories (US-*), tasks (TASK-*), and test cases.

---

*Last updated: 2026-04-14 | Author: PM Agent*
