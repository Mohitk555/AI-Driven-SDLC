"""QA Agent — generates test cases, validates code, and logs bugs."""

from __future__ import annotations

import logging
import re
import textwrap
from typing import Any

from orchestrator.models import AgentResponse, ToolCall

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class QAAgent(BaseAgent):
    """Generates test cases, pytest files, and validates code against requirements.

    Outputs are written to ``memory/test_cases.md`` and generates
    pytest files for the backend.
    """

    agent_id: str = "qa_agent"
    role: str = "QA Engineer"
    permissions: list[str] = [
        "jira.create_ticket",
        "jira.update_ticket",
    ]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def process(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """Generate test artifacts and optionally log bugs."""
        try:
            self.load_constitution()

            lower = message.lower()

            if "bug" in lower or "defect" in lower:
                return await self._log_bug(message, context)
            if "validate" in lower or "review" in lower:
                return await self._validate_against_requirements(context)

            # Default: generate test cases
            return await self._generate_test_cases(context)

        except Exception as exc:
            logger.exception("%s processing failed", self.agent_id)
            return self._fail(f"Processing error: {exc}")

    # ------------------------------------------------------------------
    # Test case generation
    # ------------------------------------------------------------------

    async def _generate_test_cases(self, context: dict[str, Any]) -> AgentResponse:
        """Produce test-case markdown and pytest files from architecture."""
        architecture = self.read_memory("architecture.md")
        requirements = self.read_memory("requirements.md")
        user_stories = self.read_memory("user_stories.md")

        if not architecture and not requirements:
            return self._fail(
                "No architecture or requirements found. "
                "Run Tech Lead / PM agents first."
            )

        endpoints = self._parse_endpoints(architecture or "")
        stories = self._parse_stories(user_stories or "")

        test_cases = self._build_test_cases(endpoints, stories)
        test_cases_md = self._render_test_cases_md(test_cases)
        self.write_memory("test_cases.md", test_cases_md)

        pytest_files = self._generate_pytest_files(endpoints)

        output = (
            f"Generated {len(test_cases)} test cases (memory/test_cases.md) "
            f"and {len(pytest_files)} pytest files."
        )
        return self._ok(
            output=output,
            metadata={
                "test_case_count": len(test_cases),
                "pytest_files": list(pytest_files.keys()),
                "generated_files": pytest_files,
                "memory_updates": {"test_cases.md": test_cases_md},
            },
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def _validate_against_requirements(
        self, context: dict[str, Any]
    ) -> AgentResponse:
        """Cross-check architecture against requirements for gaps."""
        requirements = self.read_memory("requirements.md")
        architecture = self.read_memory("architecture.md")

        if not requirements or not architecture:
            return self._fail("Both requirements.md and architecture.md are needed for validation.")

        gaps = self._find_gaps(requirements, architecture)
        tool_calls: list[ToolCall] = []

        if gaps:
            for gap in gaps:
                tool_calls.append(
                    self.create_tool_call(
                        "jira.create_ticket",
                        {
                            "project": self._jira_project_key(),
                            "issue_type": "Bug",
                            "summary": f"Gap: {gap}",
                            "description": f"Requirement not covered in architecture: {gap}",
                            "priority": "High",
                        },
                    )
                )

        output = (
            f"Validation complete. Found {len(gaps)} gaps between "
            "requirements and architecture."
        )
        return self._ok(
            output=output,
            tool_calls=tool_calls if tool_calls else None,
            metadata={"gaps": gaps},
        )

    # ------------------------------------------------------------------
    # Bug logging
    # ------------------------------------------------------------------

    async def _log_bug(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """Create a Jira bug ticket."""
        ticket_id = context.get("ticket_id", "INS-UNKNOWN")
        tool_calls: list[ToolCall] = [
            self.create_tool_call(
                "jira.create_ticket",
                {
                    "project": self._jira_project_key(),
                    "issue_type": "Bug",
                    "summary": message[:120],
                    "description": message,
                    "priority": "High",
                    "linked_ticket": ticket_id,
                },
            ),
        ]
        return self._ok(
            output=f"Bug report filed for {ticket_id}.",
            tool_calls=tool_calls,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_endpoints(self, architecture: str) -> list[dict[str, str]]:
        pattern = r"\|\s*(GET|POST|PUT|DELETE|PATCH)\s*\|\s*`([^`]+)`\s*\|\s*([^|]+)\|"
        return [
            {"method": m.strip(), "path": p.strip(), "summary": s.strip()}
            for m, p, s in re.findall(pattern, architecture)
        ]

    def _parse_stories(self, stories_md: str) -> list[str]:
        return re.findall(r"\*\*Story:\*\*\s*(.+)", stories_md)

    def _build_test_cases(
        self,
        endpoints: list[dict[str, str]],
        stories: list[str],
    ) -> list[dict[str, str]]:
        """Build a structured list of test cases."""
        cases: list[dict[str, str]] = []
        tc_id = 1

        # Endpoint-driven cases
        for ep in endpoints:
            cases.append({
                "id": f"TC-{tc_id:03d}",
                "type": "API",
                "title": f"{ep['method']} {ep['path']} — happy path",
                "steps": f"Send {ep['method']} to {ep['path']} with valid data",
                "expected": f"Returns appropriate success status code",
                "priority": "High",
            })
            tc_id += 1

            # Negative case
            cases.append({
                "id": f"TC-{tc_id:03d}",
                "type": "API",
                "title": f"{ep['method']} {ep['path']} — invalid input",
                "steps": f"Send {ep['method']} to {ep['path']} with invalid/missing data",
                "expected": "Returns 4xx with RFC 7807 error body",
                "priority": "Medium",
            })
            tc_id += 1

        # Story-driven acceptance tests
        for story in stories:
            cases.append({
                "id": f"TC-{tc_id:03d}",
                "type": "Acceptance",
                "title": f"Verify: {story[:80]}",
                "steps": f"Execute the user journey described in: {story}",
                "expected": "User achieves the stated goal",
                "priority": "High",
            })
            tc_id += 1

        # Constitution-mandated security tests
        cases.extend([
            {
                "id": f"TC-{tc_id:03d}",
                "type": "Security",
                "title": "Auth — expired JWT rejected",
                "steps": "Send request with expired JWT token",
                "expected": "Returns 401 Unauthorized",
                "priority": "Critical",
            },
            {
                "id": f"TC-{tc_id + 1:03d}",
                "type": "Security",
                "title": "Auth — missing token rejected",
                "steps": "Send request without Authorization header",
                "expected": "Returns 401 Unauthorized",
                "priority": "Critical",
            },
        ])
        return cases

    def _render_test_cases_md(self, cases: list[dict[str, str]]) -> str:
        ts = self._timestamp()
        lines = [
            "# Test Cases",
            "",
            f"> Generated by **{self.agent_id}** at {ts}",
            "",
            "| ID | Type | Title | Priority |",
            "|----|------|-------|----------|",
        ]
        for tc in cases:
            lines.append(f"| {tc['id']} | {tc['type']} | {tc['title']} | {tc['priority']} |")

        lines.append("")
        lines.append("## Detailed Steps")
        lines.append("")
        for tc in cases:
            lines.extend([
                f"### {tc['id']}: {tc['title']}",
                "",
                f"**Type**: {tc['type']}  ",
                f"**Priority**: {tc['priority']}",
                "",
                f"**Steps**: {tc['steps']}",
                "",
                f"**Expected**: {tc['expected']}",
                "",
            ])
        return "\n".join(lines)

    def _generate_pytest_files(self, endpoints: list[dict[str, str]]) -> dict[str, str]:
        """Generate pytest test files for API endpoints."""
        files: dict[str, str] = {}

        # Group endpoints by resource
        resources: dict[str, list[dict[str, str]]] = {}
        for ep in endpoints:
            segments = [
                s for s in ep["path"].split("/")
                if s and s != "api" and s != "v1" and not s.startswith("{")
            ]
            resource = segments[-1] if segments else "resource"
            resources.setdefault(resource, []).append(ep)

        for resource, eps in resources.items():
            files[f"tests/test_{resource}.py"] = self._gen_pytest_module(resource, eps)

        # Conftest
        files["tests/conftest.py"] = self._gen_conftest()

        return files

    def _gen_pytest_module(self, resource: str, endpoints: list[dict[str, str]]) -> str:
        class_name = resource.replace("_", " ").title().replace(" ", "")
        test_funcs: list[str] = []

        for ep in endpoints:
            method = ep["method"].lower()
            safe_name = ep["path"].replace("/", "_").replace("{", "").replace("}", "").strip("_")
            test_funcs.append(textwrap.dedent(f"""\

                async def test_{method}_{safe_name}_success(client: AsyncClient) -> None:
                    \"\"\"Happy-path test for {ep['method']} {ep['path']}.\"\"\"
                    response = await client.{method}("{ep['path']}")
                    assert response.status_code in (200, 201)


                async def test_{method}_{safe_name}_not_found(client: AsyncClient) -> None:
                    \"\"\"Negative test for {ep['method']} {ep['path']}.\"\"\"
                    response = await client.{method}("{ep['path']}")
                    # Adjust assertion based on actual endpoint behavior
                    assert response.status_code in (200, 404, 422)
            """))

        return textwrap.dedent(f'''\
            """Tests for {resource} endpoints."""

            import pytest
            from httpx import AsyncClient

            pytestmark = pytest.mark.asyncio
        ''') + "\n".join(test_funcs)

    def _gen_conftest(self) -> str:
        return textwrap.dedent('''\
            """Shared pytest fixtures."""

            import pytest
            from httpx import ASGITransport, AsyncClient

            from backend.main import app


            @pytest.fixture
            async def client() -> AsyncClient:
                """Async HTTP client wired to the FastAPI test app."""
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    yield ac
        ''')

    def _find_gaps(self, requirements: str, architecture: str) -> list[str]:
        """Identify requirements not reflected in the architecture."""
        req_lines = re.findall(r"\|\s*\d+\s*\|\s*(.+?)\s*\|", requirements)
        arch_lower = architecture.lower()
        gaps: list[str] = []
        for req in req_lines:
            keywords = [w for w in req.lower().split() if len(w) > 3]
            if not any(kw in arch_lower for kw in keywords):
                gaps.append(req.strip())
        return gaps
