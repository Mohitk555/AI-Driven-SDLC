"""Product Manager Agent — converts stakeholder input into structured requirements."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from orchestrator.models import AgentResponse, ToolCall

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


# MoSCoW priority buckets
_MOSCOW_BUCKETS = ("Must Have", "Should Have", "Could Have", "Won't Have")

# Simple keyword heuristics for priority assignment
_PRIORITY_KEYWORDS: dict[str, str] = {
    "critical": "Must Have",
    "must": "Must Have",
    "essential": "Must Have",
    "required": "Must Have",
    "important": "Should Have",
    "should": "Should Have",
    "nice": "Could Have",
    "could": "Could Have",
    "optional": "Could Have",
    "later": "Won't Have",
    "defer": "Won't Have",
    "future": "Won't Have",
}


class PMAgent(BaseAgent):
    """Translates stakeholder input into requirements and user stories.

    Outputs are written to ``memory/requirements.md`` and
    ``memory/user_stories.md``.  A Jira ticket creation tool-call is
    returned so the orchestrator can materialise the epic.
    """

    agent_id: str = "pm_agent"
    role: str = "Product Manager"
    permissions: list[str] = ["jira.create_ticket"]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def process(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """Parse stakeholder input, generate requirements and user stories."""
        try:
            self.load_constitution()

            # 1. Parse input into requirement items
            requirements = self._extract_requirements(message)
            if not requirements:
                return self._fail("Could not extract any requirements from the input.")

            # 2. Prioritise via MoSCoW
            prioritised = self._prioritise(requirements)

            # 3. Generate user stories
            user_stories = self._generate_user_stories(prioritised)

            # 4. Build markdown artifacts
            req_md = self._build_requirements_md(prioritised)
            stories_md = self._build_user_stories_md(user_stories)

            # 5. Persist to memory
            self.write_memory("requirements.md", req_md)
            self.write_memory("user_stories.md", stories_md)

            # 6. Prepare Jira tool-call to create an epic
            tool_calls: list[ToolCall] = []
            epic_title = self._derive_epic_title(requirements)
            tool_calls.append(
                self.create_tool_call(
                    "jira.create_ticket",
                    {
                        "project": "INS",
                        "issue_type": "Epic",
                        "summary": epic_title,
                        "description": req_md,
                        "priority": "High",
                    },
                )
            )

            output_summary = (
                f"Generated {len(requirements)} requirements and "
                f"{len(user_stories)} user stories. "
                f"Artifacts written to memory/requirements.md and memory/user_stories.md."
            )

            response = self._ok(
                output=output_summary,
                tool_calls=tool_calls,
                metadata={
                    "requirements_count": len(requirements),
                    "user_stories_count": len(user_stories),
                    "memory_updates": {
                        "requirements.md": req_md,
                        "user_stories.md": stories_md,
                    },
                },
            )

            if not self.validate_output(response.model_dump()):
                return self._fail("Output validation against constitution failed.")

            return response

        except Exception as exc:
            logger.exception("%s processing failed", self.agent_id)
            return self._fail(f"Processing error: {exc}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_requirements(self, text: str) -> list[str]:
        """Extract individual requirement statements from free-form text.

        Supports bullet lists (``-``, ``*``, numbered) as well as
        sentence-split plain paragraphs.
        """
        lines: list[str] = []
        for raw in text.strip().splitlines():
            line = raw.strip()
            # Strip common list prefixes
            line = re.sub(r"^[\-\*]\s+", "", line)
            line = re.sub(r"^\d+[\.\)]\s+", "", line)
            if line:
                lines.append(line)
        return lines

    def _prioritise(self, requirements: list[str]) -> list[dict[str, str]]:
        """Assign a MoSCoW priority to each requirement."""
        result: list[dict[str, str]] = []
        for req in requirements:
            lower = req.lower()
            priority = "Should Have"  # default
            for keyword, bucket in _PRIORITY_KEYWORDS.items():
                if keyword in lower:
                    priority = bucket
                    break
            result.append({"requirement": req, "priority": priority})
        return result

    def _generate_user_stories(
        self, prioritised: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        """Create user stories in standard format for each requirement."""
        stories: list[dict[str, str]] = []
        for item in prioritised:
            req = item["requirement"]
            story = (
                f"As an insurance platform user, "
                f"I want {req.lower().rstrip('.')}, "
                f"so that the platform meets business needs."
            )
            stories.append({
                "story": story,
                "requirement": req,
                "priority": item["priority"],
            })
        return stories

    def _build_requirements_md(self, prioritised: list[dict[str, str]]) -> str:
        """Render prioritised requirements as a markdown document."""
        ts = self._timestamp()
        lines = [
            "# Requirements",
            "",
            f"> Generated by **{self.agent_id}** at {ts}",
            "",
            "## Prioritised Requirements (MoSCoW)",
            "",
            "| # | Requirement | Priority |",
            "|---|-------------|----------|",
        ]
        for idx, item in enumerate(prioritised, 1):
            lines.append(
                f"| {idx} | {item['requirement']} | {item['priority']} |"
            )
        lines.append("")
        return "\n".join(lines)

    def _build_user_stories_md(self, stories: list[dict[str, str]]) -> str:
        """Render user stories as a markdown document."""
        ts = self._timestamp()
        lines = [
            "# User Stories",
            "",
            f"> Generated by **{self.agent_id}** at {ts}",
            "",
        ]
        for idx, s in enumerate(stories, 1):
            lines.extend([
                f"## US-{idx:03d} [{s['priority']}]",
                "",
                f"**Story:** {s['story']}",
                "",
                f"**Source requirement:** {s['requirement']}",
                "",
            ])
        return "\n".join(lines)

    @staticmethod
    def _derive_epic_title(requirements: list[str]) -> str:
        """Create a concise epic title from the first requirement."""
        first = requirements[0]
        if len(first) > 80:
            return first[:77] + "..."
        return first
