"""Abstract base class for all MCP tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolResponse(BaseModel):
    """Standardised response returned by every tool action."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class BaseTool(ABC):
    """Base class that every MCP tool must extend.

    Subclasses declare their *name*, a human-readable *description*, and the
    set of *required_params* that callers must provide.  The ``execute`` method
    contains the actual integration logic and must be implemented as an
    async coroutine.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique dot-prefix for this tool (e.g. ``jira``, ``github``)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short human-readable description of the tool."""
        ...

    @property
    @abstractmethod
    def required_params(self) -> dict[str, list[str]]:
        """Mapping of *action* -> list of required parameter names.

        Example::

            {"create_ticket": ["summary", "description"]}
        """
        ...

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run the requested action and return a ``ToolResponse``-shaped dict.

        Parameters
        ----------
        params:
            Must include an ``"action"`` key plus any action-specific fields.

        Returns
        -------
        dict with keys ``success``, ``data``, ``error``.
        """
        ...

    def validate_params(self, params: dict[str, Any]) -> bool:
        """Return ``True`` when *params* satisfies the action's requirements.

        Checks that ``"action"`` is present and that every required parameter
        for that action is included.
        """
        action: str | None = params.get("action")
        if action is None:
            return False

        required = self.required_params.get(action)
        if required is None:
            # Unknown action — let execute() handle the error.
            return False

        return all(key in params for key in required)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ok(data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Shortcut for a successful response."""
        return ToolResponse(success=True, data=data).model_dump()

    @staticmethod
    def _fail(error: str) -> dict[str, Any]:
        """Shortcut for a failed response."""
        return ToolResponse(success=False, error=error).model_dump()
