# Architecture Decision Records -- Claims Management Module

> Updated by **techlead_agent** at 2026-04-05T12:00:00Z

---

## ADR-001: Use SQLite for Development, PostgreSQL for Production

**Date:** 2026-04-05
**Status:** Accepted
**Author:** techlead_agent

**Decision:** Use SQLite as the database for local development and PostgreSQL for staging/production environments.

**Rationale:** SQLite requires zero setup for local development, making onboarding fast. SQLAlchemy ORM abstracts the database layer, so the same models and queries work with both SQLite and PostgreSQL. This gives developers a frictionless local experience while retaining PostgreSQL's robustness in production.

**Alternatives Considered:**
- PostgreSQL everywhere (via Docker) -- adds setup complexity for local dev
- MySQL -- less feature-rich than PostgreSQL, no significant advantage for this use case

---

## ADR-002: JWT for Authentication

**Date:** 2026-04-05
**Status:** Accepted
**Author:** techlead_agent

**Decision:** Use JWT (JSON Web Tokens) for user authentication with stateless access tokens.

**Rationale:** JWT is stateless, meaning the backend does not need to store session state. This simplifies horizontal scaling and works naturally with a decoupled frontend (Next.js) and backend (FastAPI) architecture. JWT is the industry standard for SPA authentication.

**Alternatives Considered:**
- Session-based auth with cookies -- requires server-side session storage, harder to scale
- OAuth2 with third-party provider -- unnecessary complexity for an internal claims system

---

## ADR-003: File Uploads Stored on Disk, Not in Database

**Date:** 2026-04-05
**Status:** Accepted
**Author:** techlead_agent

**Decision:** Store uploaded documents (PDFs, images) on the local filesystem, with only metadata stored in the database.

**Rationale:** Storing binary files in the database degrades query performance and bloats backups. Filesystem storage is simpler, faster for serving files, and can be migrated to S3 or another object store later without changing the database schema. The `documents` table stores metadata (filename, size, content type) and a reference to the stored file path.

**Alternatives Considered:**
- Store files as BLOBs in the database -- poor performance, large backups
- S3 from the start -- adds infrastructure dependency for development; planned as a future migration

---

## ADR-004: Status Enum in Code, Not a Separate Database Table

**Date:** 2026-04-05
**Status:** Accepted
**Author:** techlead_agent

**Decision:** Define claim statuses (submitted, under_review, approved, rejected) as a Python enum in application code rather than a separate `statuses` lookup table.

**Rationale:** The set of valid claim statuses is small and fixed. Using a code-level enum provides type safety, simpler queries (no joins), and easier validation. If statuses need to change, it is a code change that goes through version control and review, which is appropriate for a workflow-critical field.

**Alternatives Considered:**
- Separate `statuses` table with foreign key -- adds join complexity for no real benefit with a fixed set
- Free-form string field -- no type safety, risk of typos and invalid states

## ADR-005: Initial architecture design

**Date**: 2026-04-05T11:24:03Z
**Status**: Accepted
**Author**: techlead_agent

**Decision**: Initial architecture design

**Rationale**: Selected Next.js + FastAPI + PostgreSQL stack per constitution. Modular service-oriented backend with RESTful API layer.

**Alternatives considered**: Django (heavier), Express (weaker typing)

## ADR-006: Initial architecture design

**Date**: 2026-04-05T11:25:09Z
**Status**: Accepted
**Author**: techlead_agent

**Decision**: Initial architecture design

**Rationale**: Selected Next.js + FastAPI + PostgreSQL stack per constitution. Modular service-oriented backend with RESTful API layer.

**Alternatives considered**: Django (heavier), Express (weaker typing)

## ADR-007: Initial architecture design

**Date**: 2026-04-05T11:29:05Z
**Status**: Accepted
**Author**: techlead_agent

**Decision**: Initial architecture design

**Rationale**: Selected Next.js + FastAPI + PostgreSQL stack per constitution. Modular service-oriented backend with RESTful API layer.

**Alternatives considered**: Django (heavier), Express (weaker typing)
