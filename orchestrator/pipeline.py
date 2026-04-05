"""Autonomous SDLC Pipeline Engine.

Drives a high-level requirement through the full software development
lifecycle by chaining agents (PM -> TechLead -> Scrum -> Dev -> QA -> DevOps)
with inter-stage data passing, MCP tool execution, human intervention
checkpoints, and comprehensive state tracking.

Usage::

    from agents import AGENT_REGISTRY
    from mcp.mcp_server import MCPServer
    from orchestrator.pipeline import PipelineEngine

    agents = {aid: cls() for aid, cls in AGENT_REGISTRY.items()}
    mcp = MCPServer()
    engine = PipelineEngine(agents=agents, mcp_server=mcp)

    run = await engine.start_pipeline("Build claims module")
    print(run.status, run.current_stage)
"""

from __future__ import annotations

import enum
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from agents import AGENT_REGISTRY
from agents.base_agent import BaseAgent
from mcp.mcp_server import MCPServer
from orchestrator.models import AgentResponse, AgentStatus, ToolCall

logger = logging.getLogger(__name__)


# =====================================================================
# Enums
# =====================================================================


class PipelineStatus(str, enum.Enum):
    """Lifecycle status of a pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED_FOR_HUMAN = "paused_for_human"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStage(str, enum.Enum):
    """Ordered SDLC stages the pipeline drives through."""

    PM = "pm"
    TECHLEAD = "techlead"
    SCRUM = "scrum"
    DEVELOPMENT = "development"
    QA = "qa"
    DEVOPS = "devops"


# Execution order used by the engine.
_STAGE_ORDER: list[PipelineStage] = [
    PipelineStage.PM,
    PipelineStage.TECHLEAD,
    PipelineStage.SCRUM,
    PipelineStage.DEVELOPMENT,
    PipelineStage.QA,
    PipelineStage.DEVOPS,
]


# =====================================================================
# Pydantic models for pipeline state
# =====================================================================


class ToolCallResult(BaseModel):
    """Recorded outcome of a single MCP tool execution."""

    tool: str
    input: dict[str, Any] = Field(default_factory=dict)
    success: bool = False
    output: Any = None
    error: str | None = None


class StageResult(BaseModel):
    """What a single SDLC stage produced."""

    stage: PipelineStage
    agent_id: str
    status: AgentStatus = AgentStatus.IN_PROGRESS
    output: Any = None
    tool_calls_executed: list[ToolCallResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    error: str | None = None


class HumanIntervention(BaseModel):
    """A question the pipeline poses to a human operator."""

    intervention_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    stage: PipelineStage
    agent_id: str
    question: str
    context: dict[str, Any] = Field(default_factory=dict)
    response: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None


class PipelineRun(BaseModel):
    """Full state of a single pipeline execution."""

    pipeline_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    requirement: str = ""
    status: PipelineStatus = PipelineStatus.PENDING
    current_stage: PipelineStage = PipelineStage.PM
    stages_log: list[StageResult] = Field(default_factory=list)
    jira_tickets: list[str] = Field(default_factory=list)
    human_interventions: list[HumanIntervention] = Field(default_factory=list)
    inter_stage_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =====================================================================
# Pipeline Engine
# =====================================================================

# Maximum retries per stage before requesting human intervention.
_MAX_STAGE_RETRIES = 2


class PipelineEngine:
    """Autonomous SDLC pipeline that chains agents end-to-end.

    Parameters
    ----------
    agents:
        Mapping of ``agent_id`` to instantiated :class:`BaseAgent` objects.
    mcp_server:
        An initialised :class:`MCPServer` used to execute tool calls.
    """

    def __init__(
        self,
        agents: dict[str, BaseAgent],
        mcp_server: MCPServer,
    ) -> None:
        self._agents = agents
        self._mcp = mcp_server
        self._runs: dict[str, PipelineRun] = {}

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    async def start_pipeline(self, requirement: str) -> PipelineRun:
        """Kick off a full autonomous SDLC pipeline for *requirement*.

        The engine walks through every stage in order, feeding the output
        of each stage into the next.  If a stage fails after retries or
        explicitly requests human input, the pipeline pauses and can be
        resumed later via :meth:`resume_pipeline`.

        Returns the :class:`PipelineRun` (which may be completed, failed,
        or paused).
        """
        run = PipelineRun(requirement=requirement, status=PipelineStatus.RUNNING)
        self._runs[run.pipeline_id] = run
        logger.info(
            "Pipeline %s started for requirement: %.120s",
            run.pipeline_id,
            requirement,
        )

        await self._execute_from_current_stage(run)
        return run

    async def resume_pipeline(
        self, pipeline_id: str, human_response: str
    ) -> PipelineRun:
        """Resume a pipeline that was paused for human intervention.

        Parameters
        ----------
        pipeline_id:
            ID of the paused pipeline.
        human_response:
            The human operator's answer to the pending question.

        Raises
        ------
        ValueError
            If the pipeline does not exist or is not paused.
        """
        run = self._get_run_or_raise(pipeline_id)
        if run.status != PipelineStatus.PAUSED_FOR_HUMAN:
            raise ValueError(
                f"Pipeline {pipeline_id} is not paused (status={run.status.value})."
            )

        # Resolve the most recent unresolved intervention.
        pending = [h for h in run.human_interventions if h.response is None]
        if not pending:
            raise ValueError("No pending human interventions found.")

        intervention = pending[-1]
        intervention.response = human_response
        intervention.resolved_at = datetime.now(timezone.utc)
        logger.info(
            "Pipeline %s: human intervention %s resolved.",
            pipeline_id,
            intervention.intervention_id,
        )

        # Store the human response in inter-stage data so the retried
        # stage can access it.
        run.inter_stage_data["human_response"] = human_response
        run.status = PipelineStatus.RUNNING
        run.updated_at = datetime.now(timezone.utc)

        await self._execute_from_current_stage(run)
        return run

    def get_pipeline_status(self, pipeline_id: str) -> PipelineRun:
        """Return the current state of a pipeline run.

        Raises
        ------
        ValueError
            If the pipeline ID is not found.
        """
        return self._get_run_or_raise(pipeline_id)

    def list_pipelines(self) -> list[PipelineRun]:
        """Return all pipeline runs, most recent first."""
        return sorted(
            self._runs.values(),
            key=lambda r: r.created_at,
            reverse=True,
        )

    # -----------------------------------------------------------------
    # Core execution loop
    # -----------------------------------------------------------------

    async def _execute_from_current_stage(self, run: PipelineRun) -> None:
        """Walk through stages starting from ``run.current_stage``.

        Stops when the pipeline completes, fails, or pauses for human
        input.
        """
        start_index = _STAGE_ORDER.index(run.current_stage)

        for stage in _STAGE_ORDER[start_index:]:
            run.current_stage = stage
            run.updated_at = datetime.now(timezone.utc)
            logger.info("Pipeline %s entering stage: %s", run.pipeline_id, stage.value)

            success = await self._run_stage(run, stage)

            if run.status == PipelineStatus.PAUSED_FOR_HUMAN:
                logger.info(
                    "Pipeline %s paused at stage %s for human input.",
                    run.pipeline_id,
                    stage.value,
                )
                return

            if not success:
                run.status = PipelineStatus.FAILED
                run.updated_at = datetime.now(timezone.utc)
                logger.error(
                    "Pipeline %s failed at stage %s.", run.pipeline_id, stage.value
                )
                return

        # All stages completed.
        run.status = PipelineStatus.COMPLETED
        run.updated_at = datetime.now(timezone.utc)
        logger.info("Pipeline %s completed successfully.", run.pipeline_id)

    async def _run_stage(self, run: PipelineRun, stage: PipelineStage) -> bool:
        """Execute a single pipeline stage with retry logic.

        Returns ``True`` on success, ``False`` on hard failure.  May
        also set the run to ``PAUSED_FOR_HUMAN`` and return ``False``.
        """
        handler = self._stage_handlers.get(stage)
        if handler is None:
            logger.error("No handler registered for stage %s", stage.value)
            return False

        for attempt in range(1, _MAX_STAGE_RETRIES + 1):
            logger.info(
                "Pipeline %s | stage %s | attempt %d/%d",
                run.pipeline_id,
                stage.value,
                attempt,
                _MAX_STAGE_RETRIES,
            )
            try:
                result = await handler(self, run)

                if result.status == AgentStatus.COMPLETED:
                    return True

                if result.status == AgentStatus.BLOCKED:
                    # Agent explicitly asked for human intervention.
                    self._pause_for_human(
                        run,
                        stage=stage,
                        agent_id=result.agent_id,
                        question=str(result.output),
                        context=result.metadata,
                    )
                    return False

                # IN_PROGRESS with tool_calls is normal -- we already
                # executed them inside the handler.  Treat as success if
                # no error surfaced.
                if result.status == AgentStatus.IN_PROGRESS:
                    return True

            except Exception:
                logger.exception(
                    "Pipeline %s | stage %s | attempt %d raised an exception",
                    run.pipeline_id,
                    stage.value,
                    attempt,
                )

        # Exhausted retries -- pause for human.
        self._pause_for_human(
            run,
            stage=stage,
            agent_id=self._agent_id_for_stage(stage),
            question=(
                f"Stage '{stage.value}' failed after {_MAX_STAGE_RETRIES} retries. "
                "Please review the logs and provide guidance."
            ),
        )
        return False

    # -----------------------------------------------------------------
    # Stage handlers
    # -----------------------------------------------------------------

    async def _stage_pm(self, run: PipelineRun) -> StageResult:
        """Stage 1 -- PM: extract requirements, create user stories, create Jira Epic."""
        agent = self._get_agent("pm_agent")
        context: dict[str, Any] = {"pipeline_id": run.pipeline_id}

        response = await agent.process(run.requirement, context)
        tool_results = await self._execute_tool_calls(response, agent.agent_id)

        # Harvest Jira ticket IDs from tool results.
        self._collect_jira_tickets(run, tool_results)

        # Build inter-stage payload for downstream stages.
        memory_updates = response.metadata.get("memory_updates", {})
        run.inter_stage_data["requirements_md"] = memory_updates.get(
            "requirements.md", ""
        )
        run.inter_stage_data["user_stories_md"] = memory_updates.get(
            "user_stories.md", ""
        )
        run.inter_stage_data["requirements_count"] = response.metadata.get(
            "requirements_count", 0
        )
        run.inter_stage_data["user_stories_count"] = response.metadata.get(
            "user_stories_count", 0
        )

        stage_result = self._record_stage(
            run, PipelineStage.PM, agent.agent_id, response, tool_results
        )
        return stage_result

    async def _stage_techlead(self, run: PipelineRun) -> StageResult:
        """Stage 2 -- TechLead: design architecture, API contracts, DB schema."""
        agent = self._get_agent("techlead_agent")

        # Feed PM output forward.
        message = (
            f"Design the architecture for the following requirements.\n\n"
            f"## Requirements\n{run.inter_stage_data.get('requirements_md', '')}\n\n"
            f"## User Stories\n{run.inter_stage_data.get('user_stories_md', '')}"
        )
        context: dict[str, Any] = {
            "pipeline_id": run.pipeline_id,
            "requirements_md": run.inter_stage_data.get("requirements_md", ""),
            "user_stories_md": run.inter_stage_data.get("user_stories_md", ""),
        }

        response = await agent.process(message, context)
        tool_results = await self._execute_tool_calls(response, agent.agent_id)
        self._collect_jira_tickets(run, tool_results)

        # Capture architecture output for Scrum.
        memory_updates = response.metadata.get("memory_updates", {})
        run.inter_stage_data["architecture_md"] = memory_updates.get(
            "architecture.md", response.output or ""
        )

        return self._record_stage(
            run, PipelineStage.TECHLEAD, agent.agent_id, response, tool_results
        )

    async def _stage_scrum(self, run: PipelineRun) -> StageResult:
        """Stage 3 -- Scrum: break stories into tasks, create Jira tickets."""
        agent = self._get_agent("scrum_agent")

        message = (
            "Create sprint plan and Jira tasks for this requirement.\n\n"
            f"## User Stories\n{run.inter_stage_data.get('user_stories_md', '')}\n\n"
            f"## Architecture\n{run.inter_stage_data.get('architecture_md', '')}"
        )
        context: dict[str, Any] = {
            "pipeline_id": run.pipeline_id,
            "sprint_number": 1,
        }

        response = await agent.process(message, context)
        tool_results = await self._execute_tool_calls(response, agent.agent_id)
        self._collect_jira_tickets(run, tool_results)

        # Build the task list for Dev stage.
        tasks = response.metadata.get("memory_updates", {}).get("tasks.md", "")
        run.inter_stage_data["tasks_md"] = tasks
        run.inter_stage_data["task_count"] = response.metadata.get("task_count", 0)

        # Build structured task list with assigned Jira ticket IDs from
        # the tool results so the dev stage knows what to work on.
        run.inter_stage_data["task_tickets"] = self._map_tasks_to_tickets(
            tool_results
        )

        return self._record_stage(
            run, PipelineStage.SCRUM, agent.agent_id, response, tool_results
        )

    async def _stage_development(self, run: PipelineRun) -> StageResult:
        """Stage 4 -- Dev: for each task, branch + build + push + update Jira."""
        task_tickets: list[dict[str, Any]] = run.inter_stage_data.get(
            "task_tickets", []
        )

        all_tool_results: list[ToolCallResult] = []
        dev_outputs: list[dict[str, Any]] = []
        last_response: AgentResponse | None = None

        for task in task_tickets:
            ticket_id = task.get("ticket_id", "UNKNOWN")
            summary = task.get("summary", "")
            task_type = task.get("type", "backend")

            # Choose the right dev agent.
            if task_type == "frontend":
                agent = self._get_agent("dev_fe_agent")
            elif task_type == "testing":
                # Testing tasks are handled in the QA stage.
                continue
            else:
                agent = self._get_agent("dev_be_agent")

            # Compose a description-safe branch slug.
            slug = self._slugify(summary)
            branch_name = f"feature/{ticket_id}-{slug}"

            message = (
                f"Implement Jira ticket {ticket_id}: {summary}\n\n"
                f"Branch: {branch_name}\n"
                f"Architecture:\n{run.inter_stage_data.get('architecture_md', '')}"
            )
            context: dict[str, Any] = {
                "pipeline_id": run.pipeline_id,
                "ticket_id": ticket_id,
                "branch_name": branch_name,
            }

            response = await agent.process(message, context)
            last_response = response
            tool_results = await self._execute_tool_calls(response, agent.agent_id)
            all_tool_results.extend(tool_results)

            # Move Jira ticket In Progress -> Code Review via MCP.
            for transition_status in ("In Progress", "Code Review"):
                tr = await self._execute_single_tool(
                    agent_id=agent.agent_id,
                    tool="jira.update_ticket",
                    input_data={
                        "ticket_id": ticket_id,
                        "status": transition_status,
                    },
                )
                all_tool_results.append(tr)

            dev_outputs.append(
                {
                    "ticket_id": ticket_id,
                    "branch": branch_name,
                    "agent": agent.agent_id,
                    "output": response.output,
                }
            )

        run.inter_stage_data["dev_outputs"] = dev_outputs
        self._collect_jira_tickets(run, all_tool_results)

        # Build a synthetic response for stage recording.
        synth = last_response or AgentResponse(
            agent_id="dev_be_agent",
            status=AgentStatus.COMPLETED,
            output=f"Development complete for {len(dev_outputs)} tasks.",
        )
        return self._record_stage(
            run, PipelineStage.DEVELOPMENT, synth.agent_id, synth, all_tool_results
        )

    async def _stage_qa(self, run: PipelineRun) -> StageResult:
        """Stage 5 -- QA: generate tests, validate, pass/fail tickets."""
        agent = self._get_agent("qa_agent")
        dev_outputs: list[dict[str, Any]] = run.inter_stage_data.get(
            "dev_outputs", []
        )

        all_tool_results: list[ToolCallResult] = []
        qa_results: list[dict[str, Any]] = []
        last_response: AgentResponse | None = None

        for dev in dev_outputs:
            ticket_id = dev.get("ticket_id", "UNKNOWN")
            branch = dev.get("branch", "")

            message = (
                f"Run QA validation for ticket {ticket_id} on branch {branch}.\n\n"
                f"Dev output: {dev.get('output', '')}"
            )
            context: dict[str, Any] = {
                "pipeline_id": run.pipeline_id,
                "ticket_id": ticket_id,
                "branch": branch,
            }

            response = await agent.process(message, context)
            last_response = response
            tool_results = await self._execute_tool_calls(response, agent.agent_id)
            all_tool_results.extend(tool_results)

            # Determine pass / fail from the agent response.
            passed = response.status != AgentStatus.FAILED

            if passed:
                # Move ticket to Done.
                tr = await self._execute_single_tool(
                    agent_id=agent.agent_id,
                    tool="jira.update_ticket",
                    input_data={"ticket_id": ticket_id, "status": "Done"},
                )
                all_tool_results.append(tr)
            else:
                # Create a Bug ticket and move original back to In Progress.
                bug_tr = await self._execute_single_tool(
                    agent_id=agent.agent_id,
                    tool="jira.create_ticket",
                    input_data={
                        "project": "INS",
                        "issue_type": "Bug",
                        "summary": f"QA failure for {ticket_id}",
                        "description": str(response.output),
                        "priority": "High",
                    },
                )
                all_tool_results.append(bug_tr)

                reopen_tr = await self._execute_single_tool(
                    agent_id=agent.agent_id,
                    tool="jira.update_ticket",
                    input_data={"ticket_id": ticket_id, "status": "In Progress"},
                )
                all_tool_results.append(reopen_tr)

            qa_results.append(
                {
                    "ticket_id": ticket_id,
                    "passed": passed,
                    "output": response.output,
                }
            )

        run.inter_stage_data["qa_results"] = qa_results
        self._collect_jira_tickets(run, all_tool_results)

        synth = last_response or AgentResponse(
            agent_id="qa_agent",
            status=AgentStatus.COMPLETED,
            output=f"QA complete: {len(qa_results)} tickets validated.",
        )
        return self._record_stage(
            run, PipelineStage.QA, synth.agent_id, synth, all_tool_results
        )

    async def _stage_devops(self, run: PipelineRun) -> StageResult:
        """Stage 6 -- DevOps: merge to QA branch, run CI/CD, deploy."""
        agent = self._get_agent("devops_agent")

        dev_outputs: list[dict[str, Any]] = run.inter_stage_data.get(
            "dev_outputs", []
        )
        branches = [d.get("branch", "") for d in dev_outputs if d.get("branch")]

        message = (
            f"Merge the following feature branches to the QA branch, "
            f"run CI/CD pipeline, and deploy:\n"
            + "\n".join(f"  - {b}" for b in branches)
        )
        context: dict[str, Any] = {
            "pipeline_id": run.pipeline_id,
            "branches": branches,
            "qa_results": run.inter_stage_data.get("qa_results", []),
        }

        response = await agent.process(message, context)
        tool_results = await self._execute_tool_calls(response, agent.agent_id)
        self._collect_jira_tickets(run, tool_results)

        return self._record_stage(
            run, PipelineStage.DEVOPS, agent.agent_id, response, tool_results
        )

    # Mapping of stage enum to handler coroutine.
    _stage_handlers: dict[PipelineStage, Any] = {
        PipelineStage.PM: _stage_pm,
        PipelineStage.TECHLEAD: _stage_techlead,
        PipelineStage.SCRUM: _stage_scrum,
        PipelineStage.DEVELOPMENT: _stage_development,
        PipelineStage.QA: _stage_qa,
        PipelineStage.DEVOPS: _stage_devops,
    }

    # -----------------------------------------------------------------
    # MCP tool execution
    # -----------------------------------------------------------------

    async def _execute_tool_calls(
        self, response: AgentResponse, agent_id: str
    ) -> list[ToolCallResult]:
        """Execute every :class:`ToolCall` in an agent response via MCP.

        Returns a list of :class:`ToolCallResult` recording what happened.
        """
        results: list[ToolCallResult] = []
        for tc in response.tool_calls:
            result = await self._execute_single_tool(
                agent_id=agent_id, tool=tc.tool, input_data=tc.input
            )
            results.append(result)
        return results

    async def _execute_single_tool(
        self,
        agent_id: str,
        tool: str,
        input_data: dict[str, Any],
    ) -> ToolCallResult:
        """Execute one tool call through the MCP server."""
        logger.info("MCP execute: agent=%s tool=%s", agent_id, tool)
        try:
            mcp_result = await self._mcp.execute(
                {"type": "tool_call", "tool": tool, "input": input_data},
                agent_id=agent_id,
            )
            success = mcp_result.get("success", False)
            return ToolCallResult(
                tool=tool,
                input=input_data,
                success=success,
                output=mcp_result.get("data"),
                error=mcp_result.get("error"),
            )
        except Exception as exc:
            logger.exception("MCP execution failed for %s", tool)
            return ToolCallResult(
                tool=tool,
                input=input_data,
                success=False,
                error=str(exc),
            )

    # -----------------------------------------------------------------
    # Jira ticket collection
    # -----------------------------------------------------------------

    @staticmethod
    def _collect_jira_tickets(
        run: PipelineRun, tool_results: list[ToolCallResult]
    ) -> None:
        """Extract Jira ticket IDs from tool execution results and add them
        to the pipeline run's ``jira_tickets`` list (deduped)."""
        existing = set(run.jira_tickets)
        for tr in tool_results:
            if not tr.success or tr.output is None:
                continue
            # The Jira tool typically returns {"ticket_id": "INS-42", ...}
            data = tr.output if isinstance(tr.output, dict) else {}
            tid = data.get("ticket_id") or data.get("key") or data.get("id")
            if tid and tid not in existing:
                run.jira_tickets.append(str(tid))
                existing.add(str(tid))

    @staticmethod
    def _map_tasks_to_tickets(
        tool_results: list[ToolCallResult],
    ) -> list[dict[str, Any]]:
        """Build a list of ``{ticket_id, summary, type}`` dicts from Jira
        creation results so the dev stage knows which tickets to implement."""
        tasks: list[dict[str, Any]] = []
        for tr in tool_results:
            if not tr.success or tr.output is None:
                continue
            data = tr.output if isinstance(tr.output, dict) else {}
            tid = data.get("ticket_id") or data.get("key")
            if not tid:
                continue

            summary = tr.input.get("summary", "")
            # Infer type from summary prefix convention used by ScrumAgent.
            task_type = "backend"
            lower_summary = summary.lower()
            if lower_summary.startswith("[fe]"):
                task_type = "frontend"
            elif lower_summary.startswith("[qa]"):
                task_type = "testing"

            tasks.append(
                {"ticket_id": str(tid), "summary": summary, "type": task_type}
            )
        return tasks

    # -----------------------------------------------------------------
    # Human intervention
    # -----------------------------------------------------------------

    def _pause_for_human(
        self,
        run: PipelineRun,
        *,
        stage: PipelineStage,
        agent_id: str,
        question: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Pause the pipeline and record a human-intervention request."""
        intervention = HumanIntervention(
            stage=stage,
            agent_id=agent_id,
            question=question,
            context=context or {},
        )
        run.human_interventions.append(intervention)
        run.status = PipelineStatus.PAUSED_FOR_HUMAN
        run.updated_at = datetime.now(timezone.utc)
        logger.warning(
            "Pipeline %s paused: %s (intervention %s)",
            run.pipeline_id,
            question[:120],
            intervention.intervention_id,
        )

    # -----------------------------------------------------------------
    # Stage recording
    # -----------------------------------------------------------------

    def _record_stage(
        self,
        run: PipelineRun,
        stage: PipelineStage,
        agent_id: str,
        response: AgentResponse,
        tool_results: list[ToolCallResult],
    ) -> StageResult:
        """Create a :class:`StageResult`, append it to the run log, and
        return it for the caller to inspect."""
        result = StageResult(
            stage=stage,
            agent_id=agent_id,
            status=response.status,
            output=response.output,
            tool_calls_executed=tool_results,
            completed_at=datetime.now(timezone.utc),
        )
        run.stages_log.append(result)
        run.updated_at = datetime.now(timezone.utc)
        logger.info(
            "Pipeline %s | stage %s recorded (status=%s, tools=%d)",
            run.pipeline_id,
            stage.value,
            response.status.value,
            len(tool_results),
        )
        return result

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _get_agent(self, agent_id: str) -> BaseAgent:
        """Look up an agent by ID, raising if not found."""
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(
                f"Agent '{agent_id}' not found in registry. "
                f"Available: {list(self._agents.keys())}"
            )
        return agent

    def _get_run_or_raise(self, pipeline_id: str) -> PipelineRun:
        run = self._runs.get(pipeline_id)
        if run is None:
            raise ValueError(f"Pipeline '{pipeline_id}' not found.")
        return run

    @staticmethod
    def _agent_id_for_stage(stage: PipelineStage) -> str:
        """Return the primary agent ID for a given stage."""
        mapping: dict[PipelineStage, str] = {
            PipelineStage.PM: "pm_agent",
            PipelineStage.TECHLEAD: "techlead_agent",
            PipelineStage.SCRUM: "scrum_agent",
            PipelineStage.DEVELOPMENT: "dev_be_agent",
            PipelineStage.QA: "qa_agent",
            PipelineStage.DEVOPS: "devops_agent",
        }
        return mapping.get(stage, "unknown_agent")

    @staticmethod
    def _slugify(text: str, max_length: int = 40) -> str:
        """Convert text into a URL/branch-safe slug."""
        import re

        slug = text.lower().strip()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        if len(slug) > max_length:
            slug = slug[:max_length].rstrip("-")
        return slug or "task"
