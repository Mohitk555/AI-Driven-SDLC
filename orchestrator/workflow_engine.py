"""SDLC pipeline management.

The WorkflowEngine governs stage transitions across the lifecycle:

    REQUIREMENTS → ARCHITECTURE → TASK_PLANNING → DEVELOPMENT → TESTING → DEPLOYMENT

Each stage has configurable entry/exit criteria.  The engine validates
that exit criteria for the current stage (and entry criteria for the
next) are satisfied before allowing a transition.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from orchestrator.models import (
    AgentResponse,
    AgentStatus,
    SDLCStage,
    StageCriteria,
    WorkflowState,
)
from orchestrator.state_manager import StateManager

logger = logging.getLogger(__name__)

# Ordered stage sequence — the canonical "happy path".
STAGE_ORDER: list[SDLCStage] = [
    SDLCStage.REQUIREMENTS,
    SDLCStage.ARCHITECTURE,
    SDLCStage.TASK_PLANNING,
    SDLCStage.DEVELOPMENT,
    SDLCStage.TESTING,
    SDLCStage.DEPLOYMENT,
]

# Default entry/exit criteria per stage.
_DEFAULT_CRITERIA: dict[str, StageCriteria] = {
    SDLCStage.REQUIREMENTS.value: StageCriteria(
        entry=[],
        exit=["PRD document created", "Stakeholder approval recorded"],
    ),
    SDLCStage.ARCHITECTURE.value: StageCriteria(
        entry=["Requirements stage completed"],
        exit=["Architecture document created", "API contracts defined"],
    ),
    SDLCStage.TASK_PLANNING.value: StageCriteria(
        entry=["Architecture stage completed"],
        exit=["Sprint backlog created", "Tasks estimated"],
    ),
    SDLCStage.DEVELOPMENT.value: StageCriteria(
        entry=["Task planning stage completed"],
        exit=["All sprint tasks completed", "Code review passed"],
    ),
    SDLCStage.TESTING.value: StageCriteria(
        entry=["Development stage completed"],
        exit=["All tests passing", "Coverage targets met"],
    ),
    SDLCStage.DEPLOYMENT.value: StageCriteria(
        entry=["Testing stage completed"],
        exit=["Deployment successful", "Health checks passing"],
    ),
}


class WorkflowEngine:
    """Manages the SDLC pipeline, enforcing ordered stage transitions."""

    def __init__(self, state_manager: StateManager) -> None:
        self._state_manager = state_manager
        self._ensure_defaults()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_current_stage(self) -> SDLCStage:
        return self._state_manager.get_workflow().current_stage

    def get_workflow_state(self) -> WorkflowState:
        return self._state_manager.get_workflow()

    def can_advance(self) -> bool:
        """Return True if the current stage's exit criteria are all met."""
        wf = self._state_manager.get_workflow()
        current_idx = STAGE_ORDER.index(wf.current_stage)

        # Already at the final stage — nowhere to go.
        if current_idx >= len(STAGE_ORDER) - 1:
            return False

        return self._exit_criteria_met(wf, wf.current_stage)

    def advance_stage(self) -> WorkflowState:
        """Move to the next SDLC stage if allowed.

        Raises ValueError when transition is not permitted.
        """
        wf = self._state_manager.get_workflow()
        current_idx = STAGE_ORDER.index(wf.current_stage)

        if current_idx >= len(STAGE_ORDER) - 1:
            raise ValueError(
                f"Cannot advance beyond the final stage ({wf.current_stage.value})."
            )

        if not self._exit_criteria_met(wf, wf.current_stage):
            unmet = self._unmet_exit_criteria(wf, wf.current_stage)
            raise ValueError(
                f"Exit criteria not met for {wf.current_stage.value}: {unmet}"
            )

        next_stage = STAGE_ORDER[current_idx + 1]

        if not self._entry_criteria_met(wf, next_stage):
            unmet = self._unmet_entry_criteria(wf, next_stage)
            raise ValueError(
                f"Entry criteria not met for {next_stage.value}: {unmet}"
            )

        # Transition
        wf.stages_completed.append(wf.current_stage)
        wf.current_stage = next_stage
        wf.updated_at = datetime.utcnow()

        self._state_manager.update_workflow(wf)
        logger.info("Advanced workflow to stage: %s", next_stage.value)
        return wf

    def complete_criterion(self, stage: SDLCStage, criterion: str) -> WorkflowState:
        """Mark a single exit criterion as complete for *stage*.

        Completed criteria are tracked in workflow metadata so
        can_advance() can evaluate them.
        """
        wf = self._state_manager.get_workflow()
        key = f"_completed_criteria_{stage.value}"
        completed: list[str] = wf.stage_criteria.get(stage.value, StageCriteria()).exit
        # Store completions in metadata so we don't mutate the criteria list.
        meta_key = f"_completed_{stage.value}"
        completed_set: list[str] = wf.model_extra.get(meta_key, []) if wf.model_extra else []

        # We stash completions in the WorkflowState-level via model_copy trick:
        # Use the state manager's raw state instead.
        state = self._state_manager.get_state()
        done: list[str] = state.project_metadata.get(meta_key, [])
        if criterion not in done:
            done.append(criterion)
        state.project_metadata[meta_key] = done
        self._state_manager.update_state(project_metadata=state.project_metadata)

        logger.info("Marked criterion complete for %s: %s", stage.value, criterion)
        return self._state_manager.get_workflow()

    async def run_stage(self, stage: SDLCStage, context: dict[str, Any] | None = None) -> AgentResponse:
        """Execute the primary work for *stage*.

        In the current implementation this returns a placeholder response.
        Concrete execution will be wired once agents are implemented.
        """
        logger.info("Running stage: %s", stage.value)

        # Map stages to responsible agents.
        stage_agents: dict[SDLCStage, str] = {
            SDLCStage.REQUIREMENTS: "pm_agent",
            SDLCStage.ARCHITECTURE: "tech_lead_agent",
            SDLCStage.TASK_PLANNING: "scrum_agent",
            SDLCStage.DEVELOPMENT: "dev_backend_agent",
            SDLCStage.TESTING: "qa_agent",
            SDLCStage.DEPLOYMENT: "devops_agent",
        }

        agent_id = stage_agents.get(stage, "pm_agent")

        return AgentResponse(
            agent_id=agent_id,
            status=AgentStatus.IN_PROGRESS,
            output=f"Stage '{stage.value}' execution started.",
            metadata={"stage": stage.value, "context": context or {}},
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_defaults(self) -> None:
        """Populate default criteria if the workflow has none yet."""
        wf = self._state_manager.get_workflow()
        if not wf.stage_criteria:
            wf.stage_criteria = dict(_DEFAULT_CRITERIA)
            self._state_manager.update_workflow(wf)

    def _exit_criteria_met(self, wf: WorkflowState, stage: SDLCStage) -> bool:
        criteria = wf.stage_criteria.get(stage.value, StageCriteria())
        if not criteria.exit:
            return True
        completed = self._completed_criteria(stage)
        return all(c in completed for c in criteria.exit)

    def _entry_criteria_met(self, wf: WorkflowState, stage: SDLCStage) -> bool:
        criteria = wf.stage_criteria.get(stage.value, StageCriteria())
        if not criteria.entry:
            return True
        completed = self._completed_criteria(stage)
        return all(c in completed for c in criteria.entry)

    def _unmet_exit_criteria(self, wf: WorkflowState, stage: SDLCStage) -> list[str]:
        criteria = wf.stage_criteria.get(stage.value, StageCriteria())
        completed = self._completed_criteria(stage)
        return [c for c in criteria.exit if c not in completed]

    def _unmet_entry_criteria(self, wf: WorkflowState, stage: SDLCStage) -> list[str]:
        criteria = wf.stage_criteria.get(stage.value, StageCriteria())
        completed = self._completed_criteria(stage)
        return [c for c in criteria.entry if c not in completed]

    def _completed_criteria(self, stage: SDLCStage) -> list[str]:
        meta = self._state_manager.get_project_metadata()
        return meta.get(f"_completed_{stage.value}", [])
