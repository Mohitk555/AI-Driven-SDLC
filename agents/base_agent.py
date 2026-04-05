"""Abstract base class for all SDLC agents.

Every agent inherits from ``BaseAgent`` and must implement the
``process`` coroutine.  Shared helpers for memory I/O, tool-call
construction, and constitution-based validation live here.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.models import AgentResponse, AgentStatus, ToolCall

logger = logging.getLogger(__name__)

# Resolve the *memory/* directory relative to the project root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = _PROJECT_ROOT / "memory"


class BaseAgent(ABC):
    """Abstract base for every AI-driven SDLC agent."""

    # Subclasses MUST override these three class-level attributes.
    agent_id: str = ""
    role: str = ""
    permissions: list[str] = []

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        if not self.agent_id or not self.role:
            raise ValueError(
                f"{type(self).__name__} must define 'agent_id' and 'role'."
            )
        self._constitution: str | None = None

    def __repr__(self) -> str:
        return f"<{type(self).__name__} agent_id={self.agent_id!r}>"

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def process(self, message: str, context: dict[str, Any]) -> AgentResponse:
        """Process an incoming message and return a structured response.

        Parameters
        ----------
        message:
            Natural-language instruction or request.
        context:
            Arbitrary key-value context supplied by the orchestrator
            (e.g. ``session_id``, ``workflow_state``).
        """

    # ------------------------------------------------------------------
    # Constitution
    # ------------------------------------------------------------------

    def load_constitution(self) -> str:
        """Read and cache ``memory/constitution.md``."""
        if self._constitution is None:
            self._constitution = self.read_memory("constitution.md")
            logger.info("%s loaded constitution (%d chars)", self.agent_id, len(self._constitution))
        return self._constitution

    # ------------------------------------------------------------------
    # Memory I/O
    # ------------------------------------------------------------------

    def read_memory(self, filename: str) -> str:
        """Read a markdown file from the shared ``memory/`` directory.

        Returns an empty string if the file does not exist.
        """
        path = MEMORY_DIR / filename
        if not path.exists():
            logger.warning("%s: memory file %s not found", self.agent_id, filename)
            return ""
        return path.read_text(encoding="utf-8")

    def write_memory(self, filename: str, content: str) -> None:
        """Write (or overwrite) a markdown file in ``memory/``.

        The directory is created if it does not already exist.
        """
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        path = MEMORY_DIR / filename
        path.write_text(content, encoding="utf-8")
        logger.info("%s wrote memory/%s (%d chars)", self.agent_id, filename, len(content))

    # ------------------------------------------------------------------
    # Tool-call helpers
    # ------------------------------------------------------------------

    def create_tool_call(self, tool: str, input_data: dict[str, Any]) -> ToolCall:
        """Build a :class:`ToolCall` after validating permissions.

        Raises
        ------
        PermissionError
            If *tool* is not in the agent's ``permissions`` list.
        """
        if tool not in self.permissions:
            raise PermissionError(
                f"Agent {self.agent_id!r} is not permitted to call {tool!r}. "
                f"Allowed: {self.permissions}"
            )
        return ToolCall(type="tool_call", tool=tool, input=input_data)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_output(self, output: dict[str, Any]) -> bool:
        """Validate an output dict against core constitution rules.

        This performs lightweight structural checks.  More advanced
        semantic validation can be layered on by subclasses.
        """
        constitution = self.load_constitution()

        # Rule: every response must include agent_id, status, output (§12).
        required_keys = {"agent_id", "status", "output"}
        if not required_keys.issubset(output.keys()):
            logger.error(
                "%s: output missing required keys %s",
                self.agent_id,
                required_keys - output.keys(),
            )
            return False

        # Rule: agents must not exceed their permissions (§13).
        for tc in output.get("tool_calls", []):
            tool_name = tc.get("tool", "") if isinstance(tc, dict) else tc.tool
            if tool_name not in self.permissions:
                logger.error(
                    "%s: tool_call %s not in permissions", self.agent_id, tool_name
                )
                return False

        # Rule: failed operations must include error details (§12).
        if output.get("status") == AgentStatus.FAILED and not output.get("output"):
            logger.error("%s: failed status without error details", self.agent_id)
            return False

        return True

    # ------------------------------------------------------------------
    # Response builders
    # ------------------------------------------------------------------

    def _ok(
        self,
        output: str,
        tool_calls: list[ToolCall] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Shortcut to build a *completed* ``AgentResponse``."""
        status = AgentStatus.COMPLETED if not tool_calls else AgentStatus.IN_PROGRESS
        return AgentResponse(
            agent_id=self.agent_id,
            status=status,
            output=output,
            tool_calls=tool_calls or [],
            metadata=metadata or {},
            timestamp=datetime.now(timezone.utc),
        )

    def _fail(self, error: str) -> AgentResponse:
        """Shortcut to build a *failed* ``AgentResponse``."""
        return AgentResponse(
            agent_id=self.agent_id,
            status=AgentStatus.FAILED,
            output=error,
            timestamp=datetime.now(timezone.utc),
        )

    @staticmethod
    def _timestamp() -> str:
        """ISO-8601 UTC timestamp for memory entries."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
