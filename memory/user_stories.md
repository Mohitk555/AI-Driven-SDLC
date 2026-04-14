# User Stories — Auto Insurance Policy Management Module

> Author: PM Agent | Phase: REQUIREMENTS | Date: 2026-04-06

---

## US-001: Generate Auto Insurance Quote
- **Linked Requirement**: REQ-001, REQ-002
- **Priority**: Must Have
- **Story**: As a prospective policyholder, I want to generate an auto insurance quote by providing my vehicle and driver details, so that I can see estimated premiums and coverage options before committing.
- **Acceptance Criteria**:
  - Given I provide valid vehicle details (make, model, year, VIN, mileage) and driver details (name, DOB, license number, driving history, address), when I submit the quote form, then I receive a premium estimate with at least basic and full coverage options.
  - Given I provide incomplete or invalid data, when I submit the form, then I see field-level error messages indicating what needs correction.
  - Given valid inputs, when the premium is calculated, then the risk rules applied and their factors are logged for audit.
- **Edge Cases / Negative Scenarios**:
  - Driver under minimum insurable age (e.g., <16) — system rejects with clear message.
  - Vehicle year in the future — system rejects.
  - Duplicate VIN for same user — system warns but allows (user may re-quote).

## US-002: View Premium Breakdown
- **Linked Requirement**: REQ-002
- **Priority**: Must Have
- **Story**: As a prospective policyholder, I want to see a detailed premium breakdown showing how risk factors (driver age, violations, vehicle age, coverage level) contributed to my quote, so that I understand the pricing.
- **Acceptance Criteria**:
  - Given a generated quote, when I view the quote details, then I see a line-item breakdown of risk factor contributions to the total premium.
  - Given the breakdown, when I review it, then each factor shows label, value, and impact on premium.

## US-003: Purchase Policy from Quote
- **Linked Requirement**: REQ-003
- **Priority**: Must Have
- **Story**: As a prospective policyholder, I want to purchase a policy from my approved quote, so that I become an active policyholder with coverage.
- **Acceptance Criteria**:
  - Given I have a valid, non-expired quote, when I confirm purchase and payment succeeds, then a policy record is created with status "active", a unique policy number (format: `POL-YYYYMMDD-XXXXX`), effective date = today, and expiration date = today + 12 months.
  - Given payment fails, when I attempt purchase, then no policy is created, I see an error message, and the failure is logged.
  - Given a quote is expired (>30 days old), when I attempt purchase, then the system rejects with "quote expired" message.
- **Edge Cases / Negative Scenarios**:
  - Double-submit prevention — if policy already created for quote, reject duplicate purchase.
  - Concurrent purchase attempts — system must handle idempotently.

## US-004: Download Policy Document
- **Linked Requirement**: REQ-004
- **Priority**: Must Have
- **Story**: As an active policyholder, I want to download my policy document as a PDF, so that I have an official record of my coverage.
- **Acceptance Criteria**:
  - Given I have an active policy, when I request the document, then I receive a PDF containing: policy number, insured driver name, vehicle details, coverage type, premium amount, effective/expiration dates, and terms summary.
  - Given I request another user's policy document, then the system returns 403 Forbidden.
  - Given the policy is not active (cancelled/expired), when I request the document, then the system still allows download (historical record).

## US-005: View My Quotes
- **Linked Requirement**: REQ-005
- **Priority**: Should Have
- **Story**: As a user, I want to view a list of my past quotes with their statuses, so that I can track and revisit them.
- **Acceptance Criteria**:
  - Given I am authenticated, when I navigate to the quotes page, then I see a paginated list of my quotes showing: date, vehicle summary, coverage type, premium, and status (pending/purchased/expired).
  - Given I have no quotes, when I visit the page, then I see an empty state with a prompt to create a new quote.

## US-006: View My Policies
- **Linked Requirement**: REQ-006
- **Priority**: Should Have
- **Story**: As a policyholder, I want to view a list of my policies with their statuses, so that I can manage my insurance coverage.
- **Acceptance Criteria**:
  - Given I am authenticated, when I navigate to the policies page, then I see a paginated list of my policies showing: policy number, vehicle summary, coverage type, status (active/expired/cancelled), and effective dates.
  - Given I click on a policy, then I see full policy details and a download button for the policy document.

---

## V2 — Policy List Module Stories

## US-007: View All Policies Table (Admin/Agent)
- **Linked Requirement**: REQ-007
- **Priority**: Must Have
- **Story**: As an admin/agent user, I want to view a tabular list of all issued policies with customer and policy details, so that I can manage the policy portfolio.
- **Acceptance Criteria**:
  - Given I am an authenticated admin, when I navigate to the admin policy list, then I see a table with columns: policy number, customer name, vehicle summary, coverage type, premium, status, effective date, expiration date, and action buttons.
  - Given I apply a filter by status, when the table refreshes, then only matching policies are shown.
  - Given I search by policy number or customer name, when results load, then matching policies are displayed.
  - Given there are more than 20 policies, when I view the list, then pagination controls are visible and functional.
- **Edge Cases / Negative Scenarios**:
  - Non-admin user attempts to access admin policy list — 403 Forbidden.
  - No policies exist — empty state with informational message.

## US-008: Cancel a Policy
- **Linked Requirement**: REQ-008
- **Priority**: Must Have
- **Story**: As an admin/agent, I want to cancel an active policy with a reason, so that the policy is terminated and the action is audited.
- **Acceptance Criteria**:
  - Given an active policy, when I click "Cancel" and provide a cancellation reason, then the policy status changes to "cancelled" and I see a success confirmation.
  - Given a cancelled or expired policy, when I attempt to cancel, then the system shows "Action not allowed" error.
  - Given I try to cancel without providing a reason, then the system requires a reason before proceeding.
  - An audit log entry is created with the action, reason, actor, and timestamp.

## US-009: Renew a Policy
- **Linked Requirement**: REQ-009
- **Priority**: Must Have
- **Story**: As an admin/agent, I want to renew an active or expired policy, so that a new policy is issued with extended coverage dates.
- **Acceptance Criteria**:
  - Given an active or expired policy, when I click "Renew", then a new policy record is created with a new policy number, effective date = today, expiration = today + 12 months, and same coverage details.
  - Given the renewal succeeds, then I see the new policy in the list and can navigate to its detail page.
  - Given a cancelled policy, when I attempt to renew, then the system rejects with "Policy must be reinstated before renewal".
  - The new policy contains a `renewed_from_policy_id` reference.

## US-010: Reinstate a Cancelled Policy
- **Linked Requirement**: REQ-010
- **Priority**: Must Have
- **Story**: As an admin/agent, I want to reinstate a cancelled policy with a reason, so that the policyholder's coverage is restored.
- **Acceptance Criteria**:
  - Given a cancelled policy, when I click "Reinstate" and provide a reason, then the policy status changes to "reinstated" and I see a success confirmation.
  - Given a non-cancelled policy (active/expired/reinstated), when I attempt to reinstate, then the system shows "Action not allowed" error.
  - Given I try to reinstate without a reason, then the system requires one.
  - An audit log entry is created with the action, reason, actor, and timestamp.

---

## V3 — User-Facing Policy Renewal Stories

## US-011: See Expiry Notification Before Policy Expires
- **Linked Requirement**: REQ-011
- **Priority**: Must Have
- **Story**: As a policyholder, I want to see a notification in my portal when my policy is about to expire, so that I can take action to renew before losing coverage.
- **Acceptance Criteria**:
  - Given I have an active policy expiring within 30 days, when I view the policies list page, then I see a warning banner showing the policy number, days until expiry, and a "Renew Now" button.
  - Given I have an active policy expiring within 30 days, when I view that policy's detail page, then I see an expiry alert with a "Renew This Policy" button.
  - Given all my policies expire more than 30 days from now, when I view the policies list, then no expiry notification is shown.
  - Given a cancelled policy expiring within 30 days, when I view my policies, then no renewal notification appears for that cancelled policy.
- **Edge Cases / Negative Scenarios**:
  - Policy expires today — show urgent "Expires today" notification.
  - Policy already expired — show "Expired" state, renewal still available from detail page.
  - Multiple policies expiring soon — show notifications for each.

## US-012: Preview Renewal Premium Before Confirming
- **Linked Requirement**: REQ-012
- **Priority**: Must Have
- **Story**: As a policyholder renewing my policy, I want to see the recalculated premium with a breakdown before I confirm, so that I understand any price changes.
- **Acceptance Criteria**:
  - Given I click "Renew" on an eligible policy, when the renewal preview loads, then I see: current premium, new calculated premium, premium breakdown by risk factor, and the difference (increase/decrease).
  - Given the premium has changed due to updated driver age, when I view the breakdown, then the driver age factor reflects my current age.
  - Given I review the preview, when I decide not to proceed, then I can cancel/go back without any changes.
- **Edge Cases / Negative Scenarios**:
  - Premium increases significantly — clear display of increase amount.
  - Premium decreases — clearly shown as savings.

## US-013: Renew My Policy with One Click
- **Linked Requirement**: REQ-013
- **Priority**: Must Have
- **Story**: As a policyholder, I want to renew my policy with a single confirmation click, so that I can maintain my coverage quickly and easily.
- **Acceptance Criteria**:
  - Given I am on the renewal preview with the recalculated premium, when I click "Confirm Renewal", then a new policy is created with status "active", effective date = today, expiration = today + 12 months, and the recalculated premium.
  - Given the renewal succeeds, when I see the confirmation, then I am shown the new policy number and can navigate to the new policy detail page.
  - Given a cancelled policy, when I attempt to renew from the detail page, then the renew button is disabled/hidden with a message "Contact support to reinstate before renewal".
  - Given I already renewed this policy, when I attempt to renew again, then I see "This policy has already been renewed" with a link to the renewed policy.
- **Edge Cases / Negative Scenarios**:
  - Double-click / concurrent renewal — idempotency prevents duplicate policies.
  - Network failure during renewal — error message with retry guidance.

## US-014: View Renewed Policy Details with Renewal Chain
- **Linked Requirement**: REQ-014
- **Priority**: Must Have
- **Story**: As a policyholder, I want to view my renewed policy details and navigate between original and renewed policies, so that I can track my coverage history.
- **Acceptance Criteria**:
  - Given I have a renewed policy, when I view its detail page, then I see all standard policy details plus a "Renewed from" section linking to the original policy.
  - Given my original policy was renewed, when I view the original policy detail page, then I see a "Renewed as" section linking to the new policy.
  - Given a multi-step renewal chain (A -> B -> C), when I view policy B, then I see both "Renewed from A" and "Renewed as C" links.

---

## V4 — Configurable Risk Rules Engine Stories

## US-015: Manage Risk Rules (Admin CRUD)
- **Linked Requirement**: REQ-015
- **Priority**: Must Have
- **Story**: As an admin, I want to create, view, edit, and delete risk rules, so that I can configure which factors affect premium calculations without code changes.
- **Acceptance Criteria**:
  - Given I am an admin, when I create a rule with factor name "credit_score", brackets [{condition: "<600", adjustment: 300}, {condition: "600-750", adjustment: 0}, {condition: ">750", adjustment: -100}], and label "Credit Score", then the rule is saved and visible in the rules list.
  - Given I edit an existing rule's bracket adjustment from +200 to +250, when I save, then subsequent premium calculations use the new value.
  - Given I delete a rule, when I confirm, then the rule is soft-deleted and excluded from future calculations.
  - Given I am a regular user, when I attempt to access the rules API, then I get 403 Forbidden.
- **Edge Cases / Negative Scenarios**:
  - Creating a rule with duplicate factor name — rejected with validation error.
  - Empty brackets list — rejected (at least one bracket required).

## US-016: Enable/Disable Risk Rules Dynamically
- **Linked Requirement**: REQ-016
- **Priority**: Must Have
- **Story**: As an admin, I want to enable or disable individual risk rules without deleting them, so that I can temporarily remove factors from premium calculations and re-enable them later.
- **Acceptance Criteria**:
  - Given an enabled rule "violations", when I click "Disable", then the rule status changes to disabled and violations no longer affect new premium calculations.
  - Given a disabled rule, when I click "Enable", then the rule is re-activated and included in new calculations.
  - Given I toggle a rule, when the action completes, then an audit log entry is created recording the change.
- **Edge Cases / Negative Scenarios**:
  - Disabling all rules — premium equals base rate only (valid behavior).
  - Toggling a non-existent rule — 404 error.

## US-017: Premium Calculation Uses DB Rules
- **Linked Requirement**: REQ-017
- **Priority**: Must Have
- **Story**: As a system, when calculating a premium, I want to load risk rules from the database and apply only enabled rules, so that rule changes take effect without redeployment.
- **Acceptance Criteria**:
  - Given the default 5 rules are seeded and enabled, when a premium is calculated with the same inputs as before the refactor, then the result is identical to the previous hardcoded calculation.
  - Given an admin has added a new "credit_score" rule and it is enabled, when a premium is calculated, then the credit_score factor appears in the breakdown with the correct adjustment.
  - Given the "violations" rule is disabled, when a premium is calculated for a driver with 2 violations, then the violations factor shows $0 impact.

## US-018: View Risk Rules Admin Page
- **Linked Requirement**: REQ-018
- **Priority**: Must Have
- **Story**: As an admin, I want a dedicated page to view and manage all risk rules in a table format, so that I have clear visibility into the current premium calculation configuration.
- **Acceptance Criteria**:
  - Given I navigate to /admin/risk-rules, when the page loads, then I see a table with columns: Factor Name, Label, Status (enabled/disabled), Brackets Count, and Actions.
  - Given I click "Disable" on an enabled rule, when the toggle completes, then the status updates in-place without page reload.
  - Given I click "Edit" on a rule, when the form loads, then I can modify brackets and label, and save returns me to the list.
  - Given I click "Create New Rule", when I fill in the form and save, then the new rule appears in the list.

---

## Traceability Matrix

| User Story | Requirements |
|------------|-------------|
| US-001 | REQ-001, REQ-002 |
| US-002 | REQ-002 |
| US-003 | REQ-003 |
| US-004 | REQ-004 |
| US-005 | REQ-005 |
| US-006 | REQ-006 |
| US-007 | REQ-007 |
| US-008 | REQ-008 |
| US-009 | REQ-009 |
| US-010 | REQ-010 |
| US-011 | REQ-011 |
| US-012 | REQ-012 |
| US-013 | REQ-013 |
| US-014 | REQ-014 |
| US-015 | REQ-015 |
| US-016 | REQ-016 |
| US-017 | REQ-017 |
| US-018 | REQ-018 |
| US-019 | REQ-019 |
| US-020 | REQ-020 |
| US-021 | REQ-021 |
| US-022 | REQ-022 |

---

## V5 — Claims Analytics Dashboard Stories

## US-019: View Claims Summary Statistics
- **Linked Requirement**: REQ-019
- **Priority**: Must Have
- **Story**: As an admin, I want to see aggregated claims statistics (total filed, counts by status, total/average amounts), so that I can monitor claims volume and trends.
- **Acceptance Criteria**:
  - Given I call the dashboard endpoint, when claims exist, then I see totalClaims, countByStatus (per-status counts), totalAmount, and averageAmount.
  - Given I provide dateFrom/dateTo parameters, when the endpoint responds, then stats only reflect claims created within that range.
  - Given I provide a claimType filter, when the endpoint responds, then stats only reflect claims of that type.
  - Given no claims exist, when I call the endpoint, then totalClaims=0 and averages are null.
- **Edge Cases / Negative Scenarios**:
  - Invalid date format — 422 validation error.
  - Non-admin user — 403 Forbidden.

## US-020: View Approved vs Rejected Breakdown
- **Linked Requirement**: REQ-020
- **Priority**: Must Have
- **Story**: As an admin, I want to see the approval and rejection rates for claims, so that I can assess decision quality and identify process issues.
- **Acceptance Criteria**:
  - Given resolved claims exist, when I view the dashboard, then I see approvedCount, rejectedCount, approvalRate (%), and rejectionRate (%).
  - Given no resolved claims, when I view the dashboard, then rates are null (not 0).

## US-021: View Average Claim Processing Time
- **Linked Requirement**: REQ-021
- **Priority**: Must Have
- **Story**: As an admin, I want to see the average time it takes to process claims from submission to resolution, so that I can identify bottlenecks.
- **Acceptance Criteria**:
  - Given resolved claims with varying processing times, when I view the dashboard, then averageProcessingDays shows the mean in days (1 decimal).
  - Given no resolved claims, when I view the dashboard, then averageProcessingDays is null.

## US-022: Claims Dashboard Admin Page
- **Linked Requirement**: REQ-022
- **Priority**: Must Have
- **Story**: As an admin, I want a visual dashboard page with stat cards and filters, so that I can quickly assess claims health at a glance.
- **Acceptance Criteria**:
  - Given I navigate to /admin/claims-dashboard, when the page loads, then I see cards for: Total Claims, Approved/Rejected ratio, Average Processing Time, Average Amount, and a status breakdown table.
  - Given I apply a date range or claim type filter, when the stats reload, then all cards update.
  - Given no claims exist, when the page loads, then cards show "0" or "N/A" with an empty state.

---

## V6 — Admin Dashboard UI Stories (Frontend-Only)

## US-023: View Dashboard KPI Cards
- **Linked Requirement**: REQ-023
- **Priority**: Must Have
- **Story**: As an admin user, I want to view KPI summary cards showing Today's Sales, Total Sales, Total Orders, and Total Customers, so that I can quickly assess business performance at a glance.
- **Acceptance Criteria**:
  - Given I navigate to `/admin/dashboard`, when the page loads, then I see four KPI cards with labels, values, percentage changes, and trend sparklines.
  - Given the page is loading, when data is being fetched, then I see skeleton placeholders for each card.
  - Given no data is available, when the page loads, then cards show "0" or "N/A" with empty state styling.
  - Given an error occurs, when the fetch fails, then an error message with retry option is displayed.
- **Edge Cases / Negative Scenarios**:
  - Very large metric values — formatted with commas/abbreviations.
  - Negative percentage changes — shown in red with down arrow.

## US-024: View General Sales Activity Chart
- **Linked Requirement**: REQ-024
- **Priority**: Must Have
- **Story**: As an admin user, I want to view a line/area chart of general sales activity with a date range filter, so that I can monitor sales trends over time.
- **Acceptance Criteria**:
  - Given I am on the dashboard, when the General Sale section loads, then I see a line/area chart with time-series data.
  - Given I change the date range filter, when the selection is applied, then the chart updates to reflect the selected period.
  - Given I click "View Report", when the action triggers, then a report view or navigation occurs.
- **Edge Cases / Negative Scenarios**:
  - No data for selected range — empty chart with informational message.

## US-025: View Sales Analytics Bar Chart
- **Linked Requirement**: REQ-025
- **Priority**: Must Have
- **Story**: As an admin user, I want to view a bar chart showing sales analytics breakdown, so that I can compare sales across categories.
- **Acceptance Criteria**:
  - Given I am on the dashboard, when the Sales Analytics section loads, then I see a bar chart with category labels and values.
  - Given I change the date range filter, when the selection is applied, then the bar chart updates.
- **Edge Cases / Negative Scenarios**:
  - All values zero — bars still render at minimum height with "0" labels.

## US-026: View Recent Orders Table
- **Linked Requirement**: REQ-026
- **Priority**: Must Have
- **Story**: As an admin user, I want to view a table of recent orders showing ID, Item, Quantity, Order Date, Amount, and Status, so that I can monitor order activity.
- **Acceptance Criteria**:
  - Given I am on the dashboard, when the Recent Orders section loads, then I see a table with columns: ID, Item, Quantity, Order Date, Amount, Status, and a Details action button per row.
  - Given an order status is "PAID", when displayed, then a green success badge is shown.
  - Given an order status is "PENDING", when displayed, then a yellow/orange warning badge is shown.
  - Given no orders exist, when the table renders, then an empty state with "No recent orders" message is shown.
- **Edge Cases / Negative Scenarios**:
  - Large number of orders — only recent orders shown (no pagination needed for dashboard view).

## US-027: Dashboard Layout with Sidebar and Header
- **Linked Requirement**: REQ-027
- **Priority**: Must Have
- **Story**: As an admin user, I want the dashboard to have a sidebar navigation and a header with greeting, search, and controls, so that I can navigate the admin panel and access dashboard features.
- **Acceptance Criteria**:
  - Given I navigate to the dashboard, when the page loads, then I see a left sidebar with navigation icons, a header with greeting text, search bar, notification icon, language selector, and user avatar.
  - Given the layout renders, when compared to Figma, then spacing, typography hierarchy, and visual structure match the design reference.

---

## Traceability Matrix (V6 Additions)

| User Story | Requirements |
|------------|-------------|
| US-023 | REQ-023 |
| US-024 | REQ-024 |
| US-025 | REQ-025 |
| US-026 | REQ-026 |
| US-027 | REQ-027 |

---

*Last updated: 2026-04-14 | Author: PM Agent*
