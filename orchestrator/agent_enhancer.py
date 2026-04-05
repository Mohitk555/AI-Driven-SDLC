"""Enhanced agent orchestrator with ticket-driven workflows and smart context.

Wraps existing :class:`BaseAgent` instances to provide:
- Jira ticket-driven development flows (branch creation, status updates, PRs)
- Rich context building from shared memory files
- Automatic MCP tool execution for all agent-emitted tool calls
- Conflict detection and human-intervention flagging

Usage::

    enhancer = EnhancedAgentOrchestrator(agents, mcp_server)
    result = await enhancer.run_agent(
        agent_id="dev_be_agent",
        message="Implement the login endpoint",
        context={"session_id": "abc123", "intent": "dev_backend"},
        jira_ticket_id="AISDLC-7",
    )
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent, MEMORY_DIR
from mcp.mcp_server import MCPServer
from orchestrator.models import AgentResponse, AgentStatus, ToolCall

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

class EnhancedAgentResult(BaseModel):
    """Comprehensive result returned after an enhanced agent run."""

    agent_id: str
    status: str  # "completed", "failed", "needs_human"
    output: str
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    memory_updates: dict[str, str] = Field(
        default_factory=dict,
        description="Memory files written during this run (filename -> content).",
    )
    jira_updates: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Jira status transitions performed.",
    )
    git_operations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Git operations performed (branches created, PRs opened, etc.).",
    )
    errors: list[str] = Field(default_factory=list)
    needs_human: bool = False
    human_question: str | None = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Agents that participate in the ticket-driven development flow.
_DEV_AGENT_IDS = frozenset({"dev_be_agent", "dev_fe_agent"})

# Memory files loaded into every agent context.
_CONTEXT_MEMORY_FILES = (
    "requirements.md",
    "architecture.md",
    "user_stories.md",
    "tasks.md",
    "constitution.md",
)

# Status to transition a ticket to after code is pushed and a PR is opened.
_POST_DEV_STATUS: dict[str, str] = {
    "dev_be_agent": "Code Review",
    "dev_fe_agent": "Code Review",
    "qa_agent": "QA Testing",
}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class EnhancedAgentOrchestrator:
    """Wraps registered agents with ticket-driven workflows and smart context.

    Parameters
    ----------
    agents:
        Mapping of ``agent_id`` to :class:`BaseAgent` instances.
    mcp_server:
        The shared :class:`MCPServer` used to execute tool calls.
    """

    def __init__(self, agents: dict[str, BaseAgent], mcp_server: MCPServer) -> None:
        self._agents = agents
        self._mcp = mcp_server

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_agent(
        self,
        agent_id: str,
        message: str,
        context: dict[str, Any],
        jira_ticket_id: str | None = None,
    ) -> EnhancedAgentResult:
        """Run an agent with enhanced context, tool execution, and conflict detection.

        Parameters
        ----------
        agent_id:
            Identifier of the agent to invoke (must be present in ``self._agents``).
        message:
            Natural-language instruction forwarded to the agent.
        context:
            Caller-supplied context dict (e.g. ``session_id``, ``intent``).
        jira_ticket_id:
            Optional Jira ticket key (e.g. ``"AISDLC-7"``).  When provided the
            orchestrator drives the full ticket-based development flow for dev
            agents.

        Returns
        -------
        EnhancedAgentResult
            A rich result object containing agent output, tool results, git
            operations, Jira updates, and any detected issues.
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            return EnhancedAgentResult(
                agent_id=agent_id,
                status="failed",
                output=f"Unknown agent: {agent_id}",
                errors=[f"Agent '{agent_id}' is not registered."],
            )

        # Accumulators for the result.
        errors: list[str] = []
        tool_results: list[dict[str, Any]] = []
        jira_updates: list[dict[str, Any]] = []
        git_operations: list[dict[str, Any]] = []
        memory_updates: dict[str, str] = {}

        # 1. Build rich context ------------------------------------------------
        enriched_context = self._build_context(context)

        # 2. Ticket-driven pre-work (dev agents only) --------------------------
        jira_ticket: dict[str, Any] | None = None
        if jira_ticket_id is not None:
            jira_ticket, pre_errors, pre_tool_results, pre_jira, pre_git = (
                await self._ticket_pre_work(agent_id, jira_ticket_id)
            )
            errors.extend(pre_errors)
            tool_results.extend(pre_tool_results)
            jira_updates.extend(pre_jira)
            git_operations.extend(pre_git)

        if jira_ticket is not None:
            enriched_context["jira_ticket"] = jira_ticket

        # 3. Invoke the agent --------------------------------------------------
        try:
            response: AgentResponse = await agent.process(message, enriched_context)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent %s raised an exception", agent_id)
            return EnhancedAgentResult(
                agent_id=agent_id,
                status="failed",
                output=f"Agent raised {type(exc).__name__}: {exc}",
                tool_results=tool_results,
                jira_updates=jira_updates,
                git_operations=git_operations,
                errors=[*errors, f"Agent exception: {exc}"],
            )

        # 4. Execute emitted tool calls via MCP --------------------------------
        for tc in response.tool_calls:
            result = await self._execute_tool_call(tc, agent_id)
            tool_results.append(result)
            if not result.get("success", False):
                errors.append(
                    f"Tool '{tc.tool}' failed: {result.get('error', 'unknown')}"
                )

        # 5. Ticket-driven post-work -------------------------------------------
        if jira_ticket_id is not None and response.status != AgentStatus.FAILED:
            post_errors, post_tool_results, post_jira, post_git = (
                await self._ticket_post_work(agent_id, jira_ticket_id, response)
            )
            errors.extend(post_errors)
            tool_results.extend(post_tool_results)
            jira_updates.extend(post_jira)
            git_operations.extend(post_git)

        # 6. Collect memory writes from agent metadata -------------------------
        for filename, content in response.metadata.get("memory_updates", {}).items():
            memory_updates[filename] = content

        # 7. Conflict detection ------------------------------------------------
        needs_human, human_question = self._detect_conflicts(
            agent_id, response, tool_results, enriched_context,
        )
        errors_from_conflicts: list[str] = []
        if response.status == AgentStatus.FAILED:
            errors_from_conflicts.append(
                f"Agent '{agent_id}' returned FAILED status."
            )

        all_errors = [*errors, *errors_from_conflicts]

        # 8. Determine final status --------------------------------------------
        if needs_human:
            final_status = "needs_human"
        elif response.status == AgentStatus.FAILED or all_errors:
            final_status = "failed"
        else:
            final_status = "completed"

        return EnhancedAgentResult(
            agent_id=agent_id,
            status=final_status,
            output=str(response.output),
            tool_results=tool_results,
            memory_updates=memory_updates,
            jira_updates=jira_updates,
            git_operations=git_operations,
            errors=all_errors,
            needs_human=needs_human,
            human_question=human_question,
        )

    # ------------------------------------------------------------------
    # Context building
    # ------------------------------------------------------------------

    def _build_context(self, caller_context: dict[str, Any]) -> dict[str, Any]:
        """Enrich caller-supplied context with memory files and defaults.

        Always includes a ``session_id`` so downstream components can
        correlate log entries.
        """
        ctx: dict[str, Any] = {
            "session_id": caller_context.get("session_id", uuid.uuid4().hex),
            "intent": caller_context.get("intent", ""),
            "workflow_stage": caller_context.get("workflow_stage", ""),
            "previous_stage_output": caller_context.get("previous_stage_output", {}),
        }

        # Overlay any extra keys the caller provided.
        for key, value in caller_context.items():
            if key not in ctx:
                ctx[key] = value

        # Load shared memory files.
        for filename in _CONTEXT_MEMORY_FILES:
            key = filename.removesuffix(".md")
            ctx[key] = self._read_memory(filename)

        return ctx

    # ------------------------------------------------------------------
    # Ticket-driven helpers
    # ------------------------------------------------------------------

    async def _ticket_pre_work(
        self,
        agent_id: str,
        ticket_id: str,
    ) -> tuple[
        dict[str, Any] | None,  # jira_ticket data (or None on failure)
        list[str],              # errors
        list[dict[str, Any]],   # tool_results
        list[dict[str, Any]],   # jira_updates
        list[dict[str, Any]],   # git_operations
    ]:
        """Fetch the Jira ticket, create a branch, and move ticket to In Progress."""
        errors: list[str] = []
        tool_results: list[dict[str, Any]] = []
        jira_updates: list[dict[str, Any]] = []
        git_operations: list[dict[str, Any]] = []

        # --- Fetch ticket from Jira ------------------------------------------
        ticket_result = await self._mcp.execute(
            {"type": "tool_call", "tool": "jira.get_ticket", "input": {"ticket_id": ticket_id}},
            agent_id=agent_id,
        )
        tool_results.append(ticket_result)

        if not ticket_result.get("success"):
            errors.append(
                f"Failed to fetch Jira ticket {ticket_id}: "
                f"{ticket_result.get('error', 'unknown')}"
            )
            return None, errors, tool_results, jira_updates, git_operations

        jira_ticket: dict[str, Any] = ticket_result.get("data", {})

        # --- Create feature branch (dev agents only) -------------------------
        if agent_id in _DEV_AGENT_IDS:
            description = jira_ticket.get("summary", jira_ticket.get("description", ""))
            branch_name = self._make_branch_name(ticket_id, description)

            branch_result = await self._mcp.execute(
                {
                    "type": "tool_call",
                    "tool": "github.create_branch",
                    "input": {"branch_name": branch_name},
                },
                agent_id=agent_id,
            )
            tool_results.append(branch_result)

            if branch_result.get("success"):
                git_operations.append({"action": "create_branch", "branch": branch_name})
            else:
                errors.append(
                    f"Failed to create branch '{branch_name}': "
                    f"{branch_result.get('error', 'unknown')}"
                )

        # --- Move ticket to In Progress --------------------------------------
        status_result = await self._mcp.execute(
            {
                "type": "tool_call",
                "tool": "jira.update_ticket",
                "input": {"ticket_id": ticket_id, "status": "In Progress"},
            },
            agent_id=agent_id,
        )
        tool_results.append(status_result)

        if status_result.get("success"):
            jira_updates.append(
                {"ticket_id": ticket_id, "field": "status", "value": "In Progress"}
            )
        else:
            errors.append(
                f"Failed to update {ticket_id} to 'In Progress': "
                f"{status_result.get('error', 'unknown')}"
            )

        return jira_ticket, errors, tool_results, jira_updates, git_operations

    async def _ticket_post_work(
        self,
        agent_id: str,
        ticket_id: str,
        response: AgentResponse,
    ) -> tuple[
        list[str],              # errors
        list[dict[str, Any]],   # tool_results
        list[dict[str, Any]],   # jira_updates
        list[dict[str, Any]],   # git_operations
    ]:
        """Push code, open a PR, and advance ticket status after a dev agent completes."""
        errors: list[str] = []
        tool_results: list[dict[str, Any]] = []
        jira_updates: list[dict[str, Any]] = []
        git_operations: list[dict[str, Any]] = []

        if agent_id not in _DEV_AGENT_IDS:
            # Non-dev agents only get a status transition.
            next_status = _POST_DEV_STATUS.get(agent_id)
            if next_status:
                await self._transition_ticket(
                    agent_id, ticket_id, next_status,
                    errors, tool_results, jira_updates,
                )
            return errors, tool_results, jira_updates, git_operations

        # --- Push code --------------------------------------------------------
        description = response.metadata.get("summary", str(response.output)[:120])
        branch_name = response.metadata.get("branch_name")

        push_input: dict[str, Any] = {"message": f"{ticket_id}: {description}"}
        if branch_name:
            push_input["branch"] = branch_name

        push_result = await self._mcp.execute(
            {"type": "tool_call", "tool": "github.push_code", "input": push_input},
            agent_id=agent_id,
        )
        tool_results.append(push_result)

        if push_result.get("success"):
            git_operations.append({"action": "push_code", "message": push_input["message"]})
        else:
            errors.append(
                f"Failed to push code: {push_result.get('error', 'unknown')}"
            )

        # --- Open pull request ------------------------------------------------
        pr_input: dict[str, Any] = {
            "title": f"{ticket_id}: {description}",
            "body": f"Resolves {ticket_id}\n\n{description}",
        }
        if branch_name:
            pr_input["head"] = branch_name

        pr_result = await self._mcp.execute(
            {"type": "tool_call", "tool": "github.create_pr", "input": pr_input},
            agent_id=agent_id,
        )
        tool_results.append(pr_result)

        if pr_result.get("success"):
            git_operations.append({
                "action": "create_pr",
                "title": pr_input["title"],
                "pr_url": pr_result.get("data", {}).get("url"),
            })
        else:
            errors.append(
                f"Failed to create PR: {pr_result.get('error', 'unknown')}"
            )

        # --- Advance ticket status --------------------------------------------
        next_status = _POST_DEV_STATUS.get(agent_id, "Code Review")
        await self._transition_ticket(
            agent_id, ticket_id, next_status,
            errors, tool_results, jira_updates,
        )

        return errors, tool_results, jira_updates, git_operations

    async def _transition_ticket(
        self,
        agent_id: str,
        ticket_id: str,
        status: str,
        errors: list[str],
        tool_results: list[dict[str, Any]],
        jira_updates: list[dict[str, Any]],
    ) -> None:
        """Move a Jira ticket to *status*, appending results to the accumulators."""
        result = await self._mcp.execute(
            {
                "type": "tool_call",
                "tool": "jira.update_ticket",
                "input": {"ticket_id": ticket_id, "status": status},
            },
            agent_id=agent_id,
        )
        tool_results.append(result)
        if result.get("success"):
            jira_updates.append({"ticket_id": ticket_id, "field": "status", "value": status})
        else:
            errors.append(
                f"Failed to update {ticket_id} to '{status}': "
                f"{result.get('error', 'unknown')}"
            )

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    async def _execute_tool_call(
        self, tool_call: ToolCall, agent_id: str,
    ) -> dict[str, Any]:
        """Execute a single :class:`ToolCall` through the MCP server."""
        return await self._mcp.execute(
            {"type": "tool_call", "tool": tool_call.tool, "input": tool_call.input},
            agent_id=agent_id,
        )

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def _detect_conflicts(
        self,
        agent_id: str,
        response: AgentResponse,
        tool_results: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Inspect agent output and tool results for issues requiring human review.

        Returns
        -------
        (needs_human, human_question)
            A boolean flag and an optional question to surface to a human.
        """
        issues: list[str] = []

        # 1. Agent reported failure.
        if response.status == AgentStatus.FAILED:
            issues.append(f"Agent '{agent_id}' reported failure: {response.output}")

        # 2. Any tool call returned an error.
        failed_tools = [
            r for r in tool_results if not r.get("success", False)
        ]
        if failed_tools:
            tools_str = ", ".join(r.get("tool", "unknown") for r in failed_tools)
            issues.append(f"Tool call(s) failed: {tools_str}")

        # 3. Missing critical memory files.
        missing = [
            f for f in ("requirements", "architecture")
            if not context.get(f)
        ]
        if missing:
            issues.append(f"Missing required memory files: {', '.join(missing)}")

        # 4. Requirements / architecture inconsistency heuristic.
        reqs = context.get("requirements", "")
        arch = context.get("architecture", "")
        intent = str(context.get("intent", "")).lower()
        if reqs and arch and (agent_id == "techlead_agent" or intent in {"architecture", "requirements"}):
            if not self._memory_cross_references(reqs, arch):
                issues.append(
                    "Architecture document does not appear to reference any "
                    "requirement headings -- potential inconsistency."
                )

        if not issues:
            return False, None

        question = (
            "The following issues were detected and may need human review:\n"
            + "\n".join(f"  - {i}" for i in issues)
        )
        return True, question

    @staticmethod
    def _memory_cross_references(requirements: str, architecture: str) -> bool:
        """Return ``True`` if the architecture doc references at least one requirement heading.

        This is a lightweight heuristic: it extracts markdown headings from
        the requirements file and checks whether any appear (case-insensitively)
        in the architecture document.
        """
        headings = re.findall(r"^#{1,3}\s+(.+)", requirements, re.MULTILINE)
        if not headings:
            # No structured headings to compare -- skip the check.
            return True
        arch_lower = architecture.lower()
        return any(h.strip().lower() in arch_lower for h in headings)

    # ------------------------------------------------------------------
    # Memory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_memory(filename: str) -> str:
        """Read a file from the shared ``memory/`` directory.

        Returns an empty string when the file does not exist.
        """
        path = MEMORY_DIR / filename
        if not path.exists():
            logger.debug("Memory file not found: %s", path)
            return ""
        return path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Branch-name helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify(text: str, max_length: int = 48) -> str:
        """Convert *text* to a lowercase, hyphen-separated slug."""
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        # Truncate to max_length without splitting mid-word.
        if len(slug) <= max_length:
            return slug
        truncated = slug[:max_length]
        last_hyphen = truncated.rfind("-")
        if last_hyphen > 0:
            return truncated[:last_hyphen]
        return truncated

    @classmethod
    def _make_branch_name(cls, ticket_id: str, description: str) -> str:
        """Build a feature branch name from a ticket ID and description.

        Example::

            >>> EnhancedAgentOrchestrator._make_branch_name(
            ...     "AISDLC-7", "Implement login endpoint"
            ... )
            'feature/AISDLC-7-implement-login-endpoint'
        """
        slug = cls._slugify(description)
        return f"feature/{ticket_id}-{slug}"
