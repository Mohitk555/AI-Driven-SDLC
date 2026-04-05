"""Tech Lead Agent — system architecture, API contracts, and technical decisions."""

from __future__ import annotations

import logging
import re
from typing import Any

from orchestrator.models import AgentResponse, ToolCall

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TechLeadAgent(BaseAgent):
    """Designs system architecture, defines API contracts and DB schemas,
    and records technical decisions.

    Primary outputs:
    - ``memory/architecture.md``
    - ``memory/decisions.md``
    """

    agent_id: str = "techlead_agent"
    role: str = "Tech Lead"
    permissions: list[str] = ["github.create_branch"]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def process(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """Route message to the appropriate technical workflow."""
        try:
            self.load_constitution()

            lower = message.lower()

            if "architect" in lower or "design" in lower:
                return await self._design_architecture(message, context)
            if "api" in lower or "contract" in lower or "endpoint" in lower:
                return await self._define_api_contracts(message, context)
            if "database" in lower or "schema" in lower or "model" in lower:
                return await self._define_database_schema(message, context)
            if "decision" in lower or "adr" in lower:
                return await self._record_decision(message, context)

            # Default: full architecture pass
            return await self._design_architecture(message, context)

        except Exception as exc:
            logger.exception("%s processing failed", self.agent_id)
            return self._fail(f"Processing error: {exc}")

    # ------------------------------------------------------------------
    # Architecture design
    # ------------------------------------------------------------------

    async def _design_architecture(
        self, message: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Produce a system architecture document from requirements."""
        requirements = self.read_memory("requirements.md")
        tasks = self.read_memory("tasks.md")

        components = self._identify_components(requirements or message)
        api_contracts = self._draft_api_contracts(components)
        db_schema = self._draft_db_schema(components)

        arch_md = self._build_architecture_md(components, api_contracts, db_schema)
        self.write_memory("architecture.md", arch_md)

        decision_md = self._append_decision(
            title="Initial architecture design",
            rationale=(
                "Selected Next.js + FastAPI + PostgreSQL stack per constitution. "
                "Modular service-oriented backend with RESTful API layer."
            ),
            alternatives="Django (heavier), Express (weaker typing)",
        )
        self.write_memory("decisions.md", decision_md)

        tool_calls: list[ToolCall] = [
            self.create_tool_call(
                "github.create_branch",
                {
                    "branch_name": "feature/INS-001-initial-architecture",
                    "base_ref": "develop",
                },
            ),
        ]

        output = (
            f"Architecture designed with {len(components)} components. "
            "Written to memory/architecture.md and memory/decisions.md."
        )
        return self._ok(
            output=output,
            tool_calls=tool_calls,
            metadata={
                "component_count": len(components),
                "memory_updates": {
                    "architecture.md": arch_md,
                    "decisions.md": decision_md,
                },
            },
        )

    # ------------------------------------------------------------------
    # API contracts
    # ------------------------------------------------------------------

    async def _define_api_contracts(
        self, message: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Generate OpenAPI-style API contract definitions."""
        arch = self.read_memory("architecture.md")
        components = self._identify_components(arch or message)
        contracts = self._draft_api_contracts(components)

        # Append API section to architecture
        arch_content = self.read_memory("architecture.md")
        if arch_content and "## API Contracts" not in arch_content:
            arch_content += "\n" + self._render_api_section(contracts)
            self.write_memory("architecture.md", arch_content)

        output = f"Defined API contracts for {len(contracts)} endpoints."
        return self._ok(output=output, metadata={"endpoints": len(contracts)})

    # ------------------------------------------------------------------
    # Database schema
    # ------------------------------------------------------------------

    async def _define_database_schema(
        self, message: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Generate database schema definitions."""
        arch = self.read_memory("architecture.md")
        components = self._identify_components(arch or message)
        schema = self._draft_db_schema(components)

        arch_content = self.read_memory("architecture.md")
        if arch_content and "## Database Schema" not in arch_content:
            arch_content += "\n" + self._render_db_section(schema)
            self.write_memory("architecture.md", arch_content)

        output = f"Defined database schema with {len(schema)} tables."
        return self._ok(output=output, metadata={"tables": len(schema)})

    # ------------------------------------------------------------------
    # Technical decisions
    # ------------------------------------------------------------------

    async def _record_decision(
        self, message: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Append a new ADR entry to decisions.md."""
        decision_md = self._append_decision(
            title=message[:120],
            rationale="Based on project requirements and constitution constraints.",
            alternatives="N/A",
        )
        self.write_memory("decisions.md", decision_md)
        return self._ok(output="Decision recorded in memory/decisions.md.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _identify_components(self, text: str) -> list[dict[str, str]]:
        """Derive system components from requirements text."""
        # Insurance-domain default components
        defaults = [
            {"name": "Auth Service", "description": "JWT authentication and authorization"},
            {"name": "Policy Service", "description": "Policy CRUD and lifecycle management"},
            {"name": "Claims Service", "description": "Claims submission, review, and settlement"},
            {"name": "User Service", "description": "User profile and role management"},
            {"name": "Notification Service", "description": "Email, SMS, and push notifications"},
        ]

        # Scan for additional domain hints
        extra_keywords: dict[str, dict[str, str]] = {
            "payment": {"name": "Payment Service", "description": "Premium payments and billing"},
            "quote": {"name": "Quoting Service", "description": "Insurance quote generation"},
            "document": {"name": "Document Service", "description": "Document upload and storage"},
            "report": {"name": "Reporting Service", "description": "Analytics and reporting dashboards"},
            "audit": {"name": "Audit Service", "description": "Audit logging and compliance"},
        }

        lower = text.lower()
        components = list(defaults)
        for kw, comp in extra_keywords.items():
            if kw in lower and comp not in components:
                components.append(comp)

        return components

    def _draft_api_contracts(
        self, components: list[dict[str, str]]
    ) -> list[dict[str, Any]]:
        """Generate OpenAPI-style endpoint definitions for each component."""
        endpoints: list[dict[str, Any]] = []
        for comp in components:
            prefix = comp["name"].lower().replace(" service", "").replace(" ", "-")
            base = f"/api/v1/{prefix}s"
            endpoints.extend([
                {
                    "path": base,
                    "method": "GET",
                    "summary": f"List all {prefix}s",
                    "component": comp["name"],
                    "response": "200 — array of resources",
                },
                {
                    "path": base,
                    "method": "POST",
                    "summary": f"Create a new {prefix}",
                    "component": comp["name"],
                    "response": "201 — created resource",
                },
                {
                    "path": f"{base}/{{id}}",
                    "method": "GET",
                    "summary": f"Get {prefix} by ID",
                    "component": comp["name"],
                    "response": "200 — single resource",
                },
                {
                    "path": f"{base}/{{id}}",
                    "method": "PUT",
                    "summary": f"Update {prefix}",
                    "component": comp["name"],
                    "response": "200 — updated resource",
                },
            ])
        return endpoints

    def _draft_db_schema(
        self, components: list[dict[str, str]]
    ) -> list[dict[str, Any]]:
        """Generate table definitions for the database."""
        tables: list[dict[str, Any]] = []
        for comp in components:
            table_name = (
                comp["name"].lower().replace(" service", "").replace(" ", "_") + "s"
            )
            tables.append({
                "table": table_name,
                "columns": [
                    {"name": "id", "type": "UUID", "constraints": "PRIMARY KEY DEFAULT gen_random_uuid()"},
                    {"name": "created_at", "type": "TIMESTAMPTZ", "constraints": "NOT NULL DEFAULT now()"},
                    {"name": "updated_at", "type": "TIMESTAMPTZ", "constraints": "NOT NULL DEFAULT now()"},
                    {"name": "status", "type": "VARCHAR(50)", "constraints": "NOT NULL DEFAULT 'active'"},
                ],
                "indexes": [f"idx_{table_name}_status", f"idx_{table_name}_created_at"],
            })
        return tables

    # ------------------------------------------------------------------
    # Markdown renderers
    # ------------------------------------------------------------------

    def _build_architecture_md(
        self,
        components: list[dict[str, str]],
        endpoints: list[dict[str, Any]],
        tables: list[dict[str, Any]],
    ) -> str:
        ts = self._timestamp()
        lines = [
            "# System Architecture",
            "",
            f"> Generated by **{self.agent_id}** at {ts}",
            "",
            "## Tech Stack",
            "",
            "- **Frontend**: Next.js 14 + TypeScript 5 + TailwindCSS",
            "- **Backend**: FastAPI + Python 3.11+",
            "- **Database**: PostgreSQL 16",
            "- **Cache**: Redis",
            "- **Auth**: JWT (access 15min, refresh 7d)",
            "",
            "## Components",
            "",
            "| Component | Description |",
            "|-----------|-------------|",
        ]
        for c in components:
            lines.append(f"| {c['name']} | {c['description']} |")
        lines.append("")
        lines.append(self._render_api_section(endpoints))
        lines.append(self._render_db_section(tables))
        return "\n".join(lines)

    def _render_api_section(self, endpoints: list[dict[str, Any]]) -> str:
        lines = [
            "## API Contracts",
            "",
            "| Method | Path | Summary | Response |",
            "|--------|------|---------|----------|",
        ]
        for ep in endpoints:
            lines.append(
                f"| {ep['method']} | `{ep['path']}` | {ep['summary']} | {ep['response']} |"
            )
        lines.append("")
        return "\n".join(lines)

    def _render_db_section(self, tables: list[dict[str, Any]]) -> str:
        lines = ["## Database Schema", ""]
        for t in tables:
            lines.append(f"### `{t['table']}`")
            lines.append("")
            lines.append("| Column | Type | Constraints |")
            lines.append("|--------|------|-------------|")
            for col in t["columns"]:
                lines.append(f"| {col['name']} | {col['type']} | {col['constraints']} |")
            lines.append("")
            lines.append(f"**Indexes**: {', '.join(t['indexes'])}")
            lines.append("")
        return "\n".join(lines)

    def _append_decision(
        self, title: str, rationale: str, alternatives: str
    ) -> str:
        """Build or append to the decisions markdown document."""
        ts = self._timestamp()
        existing = self.read_memory("decisions.md")

        # Determine next ADR number
        nums = re.findall(r"## ADR-(\d+)", existing)
        next_num = max((int(n) for n in nums), default=0) + 1

        new_entry = "\n".join([
            f"## ADR-{next_num:03d}: {title}",
            "",
            f"**Date**: {ts}",
            f"**Status**: Accepted",
            f"**Author**: {self.agent_id}",
            "",
            f"**Decision**: {title}",
            "",
            f"**Rationale**: {rationale}",
            "",
            f"**Alternatives considered**: {alternatives}",
            "",
        ])

        if existing:
            return existing.rstrip() + "\n\n" + new_entry
        return (
            "# Architecture Decision Records\n\n"
            f"> Maintained by **{self.agent_id}**\n\n" + new_entry
        )
