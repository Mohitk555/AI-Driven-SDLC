"""Scrum Master Agent — sprint planning, task breakdown, and ceremony coordination."""

from __future__ import annotations

import logging
import re
from typing import Any

from orchestrator.models import AgentResponse, ToolCall

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Default sprint duration in days
_DEFAULT_SPRINT_DAYS = 14
_DEFAULT_STORY_POINTS = 5


class ScrumAgent(BaseAgent):
    """Manages sprint planning, task breakdown, and team coordination.

    Reads ``memory/requirements.md`` and ``memory/user_stories.md`` to
    produce ``memory/tasks.md`` and sprint plans.  Interacts with Jira,
    Slack, and Calendar via tool-calls.
    """

    agent_id: str = "scrum_agent"
    role: str = "Scrum Master"
    permissions: list[str] = [
        "jira.create_ticket",
        "jira.update_ticket",
        "jira.get_ticket",
        "jira.get_sprint",
        "slack.send_message",
        "calendar.get_events",
    ]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def process(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """Route the message to the appropriate scrum workflow."""
        try:
            self.load_constitution()

            lower = message.lower()

            if "sprint plan" in lower or "plan sprint" in lower:
                return await self._create_sprint_plan(message, context)
            if (
                "sprint status" in lower
                or "ticket status" in lower
                or "status report" in lower
                or "report sprint" in lower
                or "report ticket" in lower
                or re.search(r"\bstatus of\b", lower)
            ):
                return await self._sprint_status(message, context)
            if "task" in lower or "break" in lower:
                return await self._break_into_tasks(message, context)

            # Default: create sprint plan from available requirements
            return await self._create_sprint_plan(message, context)

        except Exception as exc:
            logger.exception("%s processing failed", self.agent_id)
            return self._fail(f"Processing error: {exc}")

    # ------------------------------------------------------------------
    # Sprint planning
    # ------------------------------------------------------------------

    async def _create_sprint_plan(
        self, message: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Build a sprint plan from requirements and user stories."""
        requirements_md = self.read_memory("requirements.md")
        stories_md = self.read_memory("user_stories.md")

        if not requirements_md and not stories_md:
            return self._fail(
                "No requirements or user stories found in memory. "
                "Run the PM Agent first to generate them."
            )

        tasks = self._parse_stories_into_tasks(stories_md or requirements_md)
        tasks_md = self._build_tasks_md(tasks)
        self.write_memory("tasks.md", tasks_md)

        sprint_number = context.get("sprint_number", 1)

        tool_calls: list[ToolCall] = []

        # Create Jira tickets for each task
        for task in tasks:
            tool_calls.append(
                self.create_tool_call(
                    "jira.create_ticket",
                    {
                        "project": self._jira_project_key(),
                        "issue_type": "Task",
                        "summary": task["title"],
                        "description": task["description"],
                        "priority": task["priority"],
                        "story_points": task["story_points"],
                        "sprint": f"Sprint {sprint_number}",
                    },
                )
            )

        # Notify team via Slack
        tool_calls.append(
            self.create_tool_call(
                "slack.send_message",
                {
                    "channel": self._slack_default_channel(),
                    "text": (
                        f"Sprint {sprint_number} plan created with "
                        f"{len(tasks)} tasks. Review tasks in Jira."
                    ),
                },
            )
        )

        # Check calendar for sprint ceremonies
        tool_calls.append(
            self.create_tool_call(
                "calendar.get_events",
                {
                    "max_results": 10,
                },
            )
        )

        total_points = sum(t["story_points"] for t in tasks)
        output = (
            f"Sprint {sprint_number} plan created: {len(tasks)} tasks, "
            f"{total_points} story points. Tasks written to memory/tasks.md."
        )

        return self._ok(
            output=output,
            tool_calls=tool_calls,
            metadata={
                "sprint_number": sprint_number,
                "task_count": len(tasks),
                "total_story_points": total_points,
                "memory_updates": {"tasks.md": tasks_md},
            },
        )

    # ------------------------------------------------------------------
    # Sprint status
    # ------------------------------------------------------------------

    async def _sprint_status(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """Generate a sprint or ticket status report."""
        ticket_key = self._extract_ticket_key(message)
        sprint_number = context.get("sprint_number", 1)

        if ticket_key:
            tool_calls: list[ToolCall] = [
                self.create_tool_call(
                    "jira.get_ticket",
                    {"ticket_key": ticket_key},
                ),
            ]
            output = f"Ticket status requested for {ticket_key}. Fetching latest status from Jira."
            return self._ok(
                output=output,
                tool_calls=tool_calls,
                metadata={"ticket_key": ticket_key},
            )

        tool_calls = [
            self.create_tool_call(
                "jira.get_sprint",
                {"board_id": context.get("jira_board_id", self._jira_board_id())},
            ),
        ]

        output = (
            f"Sprint {sprint_number} status report requested. "
            "Fetching latest data from Jira."
        )

        return self._ok(
            output=output,
            tool_calls=tool_calls,
            metadata={"sprint_number": sprint_number},
        )

    def _extract_ticket_key(self, text: str) -> str | None:
        match = re.search(r"\b([A-Z][A-Z0-9]+-\d+)\b", text)
        return match.group(1) if match else None

    # ------------------------------------------------------------------
    # Task breakdown
    # ------------------------------------------------------------------

    async def _break_into_tasks(
        self, message: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Break a requirement or story into granular tasks."""
        stories_md = self.read_memory("user_stories.md")
        tasks = self._parse_stories_into_tasks(stories_md or message)
        tasks_md = self._build_tasks_md(tasks)
        self.write_memory("tasks.md", tasks_md)

        output = f"Broke input into {len(tasks)} tasks. Written to memory/tasks.md."
        return self._ok(
            output=output,
            metadata={
                "task_count": len(tasks),
                "memory_updates": {"tasks.md": tasks_md},
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_stories_into_tasks(self, text: str) -> list[dict[str, Any]]:
        """Convert user-story markdown into task dicts.

        Each story is split into backend, frontend, and test sub-tasks.
        """
        stories = re.findall(r"##\s+US-\d+.*?\n\n\*\*Story:\*\*\s*(.+)", text)
        if not stories:
            # Fallback: treat each non-empty line as a work item
            stories = [
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.startswith("#") and not line.startswith(">")
            ]

        tasks: list[dict[str, Any]] = []
        for idx, story in enumerate(stories, 1):
            short = story[:60].rstrip(".")
            tasks.extend([
                {
                    "id": f"TASK-{idx:03d}a",
                    "title": f"[BE] {short}",
                    "description": f"Backend implementation for: {story}",
                    "type": "backend",
                    "priority": "High",
                    "story_points": _DEFAULT_STORY_POINTS,
                    "status": "To Do",
                },
                {
                    "id": f"TASK-{idx:03d}b",
                    "title": f"[FE] {short}",
                    "description": f"Frontend implementation for: {story}",
                    "type": "frontend",
                    "priority": "Medium",
                    "story_points": _DEFAULT_STORY_POINTS,
                    "status": "To Do",
                },
                {
                    "id": f"TASK-{idx:03d}c",
                    "title": f"[QA] Test: {short}",
                    "description": f"Write tests for: {story}",
                    "type": "testing",
                    "priority": "Medium",
                    "story_points": 3,
                    "status": "To Do",
                },
            ])
        return tasks

    def _build_tasks_md(self, tasks: list[dict[str, Any]]) -> str:
        """Render tasks as a markdown table."""
        ts = self._timestamp()
        lines = [
            "# Sprint Tasks",
            "",
            f"> Generated by **{self.agent_id}** at {ts}",
            "",
            "| ID | Title | Type | Priority | SP | Status |",
            "|----|-------|------|----------|----|--------|",
        ]
        for t in tasks:
            lines.append(
                f"| {t['id']} | {t['title']} | {t['type']} "
                f"| {t['priority']} | {t['story_points']} | {t['status']} |"
            )
        lines.append("")
        return "\n".join(lines)
