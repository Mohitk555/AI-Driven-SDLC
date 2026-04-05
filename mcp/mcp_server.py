"""Central MCP (Model Context Protocol) server.

Manages tool registration, permission enforcement, and execution dispatch
for all agents in the AI Engineering OS.
"""

from __future__ import annotations

import fnmatch
import logging
from typing import Any

from pydantic import BaseModel, Field

from mcp.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ======================================================================
# Request / Response models
# ======================================================================

class ToolCallRequest(BaseModel):
    """Validated shape of an incoming tool call."""

    type: str = "tool_call"
    tool: str = Field(..., description="Qualified tool name, e.g. 'jira.create_ticket'")
    input: dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    """Standardised response wrapper returned to the caller."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


# ======================================================================
# Permission matrix
# ======================================================================

PERMISSION_MATRIX: dict[str, list[str]] = {
    "scrum_agent": ["jira.*", "slack.*", "calendar.*"],
    "dev_be_agent": ["github.*", "jira.update_ticket"],
    "dev_fe_agent": ["github.*", "jira.update_ticket"],
    "qa_agent": ["jira.create_ticket", "jira.update_ticket"],
    "devops_agent": ["github.*"],
    "techlead_agent": ["github.create_branch"],
    "pm_agent": ["jira.create_ticket"],
}


# ======================================================================
# MCP Server
# ======================================================================

class MCPServer:
    """Central orchestration point for MCP tool calls.

    Usage::

        server = MCPServer()
        server.register_tool("jira", JiraTool())
        result = await server.execute({
            "type": "tool_call",
            "tool": "jira.create_ticket",
            "input": {"summary": "New feature", "issue_type": "Story"},
        })
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_tool(self, name: str, tool: BaseTool) -> None:
        """Register a tool under the given *name*.

        Parameters
        ----------
        name:
            Short identifier used as the prefix in qualified tool calls
            (e.g. ``"jira"``).
        tool:
            An instance of a :class:`BaseTool` subclass.
        """
        if name in self._tools:
            logger.warning("Overwriting previously registered tool: %s", name)
        self._tools[name] = tool
        logger.info("Registered MCP tool: %s", name)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def get_available_tools(self) -> list[str]:
        """Return the names of all currently registered tools."""
        return list(self._tools.keys())

    # ------------------------------------------------------------------
    # Permission check
    # ------------------------------------------------------------------

    def check_permission(self, agent_id: str, tool_name: str) -> bool:
        """Return ``True`` if *agent_id* is allowed to invoke *tool_name*.

        *tool_name* should be the fully-qualified name (e.g.
        ``"jira.create_ticket"``).  Permissions are checked against
        :data:`PERMISSION_MATRIX` using ``fnmatch``-style glob patterns.
        """
        allowed_patterns = PERMISSION_MATRIX.get(agent_id, [])
        return any(fnmatch.fnmatch(tool_name, pattern) for pattern in allowed_patterns)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, tool_call: dict[str, Any], agent_id: str | None = None) -> dict[str, Any]:
        """Execute a tool call and return a structured result.

        Parameters
        ----------
        tool_call:
            A dict matching the :class:`ToolCallRequest` schema::

                {
                    "type": "tool_call",
                    "tool": "jira.create_ticket",
                    "input": { ... }
                }

        agent_id:
            Optional caller identity.  When provided the server will verify
            that the agent has permission before executing.

        Returns
        -------
        dict with keys ``success``, ``data``, ``error``.
        """
        try:
            # --- Validate request shape --------------------------------
            try:
                request = ToolCallRequest(**tool_call)
            except Exception:  # noqa: BLE001
                return self._error("Malformed tool call request.")

            qualified_name = request.tool  # e.g. "jira.create_ticket"

            # --- Permission gate ---------------------------------------
            if agent_id and not self.check_permission(agent_id, qualified_name):
                return self._error(
                    f"Agent '{agent_id}' is not permitted to call '{qualified_name}'."
                )

            # --- Resolve tool and action --------------------------------
            parts = qualified_name.split(".", maxsplit=1)
            if len(parts) != 2:
                return self._error(
                    f"Tool name must be in '<tool>.<action>' format. Got: '{qualified_name}'"
                )

            tool_key, action = parts

            tool = self._tools.get(tool_key)
            if tool is None:
                return self._error(f"Tool '{tool_key}' is not registered.")

            # --- Execute ------------------------------------------------
            params = {**request.input, "action": action}
            result = await tool.execute(params)
            return result

        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled error during MCP execution")
            return self._error(f"Internal MCP error: {type(exc).__name__}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _error(message: str) -> dict[str, Any]:
        return ToolCallResponse(success=False, error=message).model_dump()
