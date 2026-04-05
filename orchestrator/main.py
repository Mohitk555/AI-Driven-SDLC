"""FastAPI application — the orchestrator's HTTP / WebSocket entry point.

Endpoints
---------
GET  /health                          — shallow health check
GET  /ready                           — deep readiness check
POST /api/v1/chat                     — single-agent chat
WS   /ws/chat                         — streaming chat over WebSocket
GET  /api/v1/workflow                 — current SDLC workflow state
POST /api/v1/workflow/advance         — advance SDLC to next stage
POST /api/v1/workflow/complete-criterion — mark exit criterion done
GET  /api/v1/agents                   — list all registered agents
POST /api/v1/tools/execute            — manually execute a tool call via MCP
POST /api/v1/pipeline/start           — start autonomous SDLC pipeline
GET  /api/v1/pipeline/{pipeline_id}   — get pipeline status
POST /api/v1/pipeline/{pipeline_id}/resume — resume pipeline after human input
GET  /api/v1/pipeline                 — list all pipelines
POST /api/v1/scheduler/start          — start background scheduler
POST /api/v1/scheduler/stop           — stop background scheduler
GET  /api/v1/scheduler                — get scheduler status
POST /api/v1/scheduler/standup        — trigger manual standup
POST /api/v1/scheduler/status-update  — trigger manual status update
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import AGENT_REGISTRY
from agents.base_agent import BaseAgent
from mcp.mcp_server import MCPServer
from mcp.tools.calendar_tool import CalendarTool
from mcp.tools.github_tool import GitHubTool
from mcp.tools.jira_tool import JiraTool
from mcp.tools.slack_tool import SlackTool
from orchestrator.agent_enhancer import EnhancedAgentOrchestrator
from orchestrator.models import (
    AgentResponse,
    AgentStatus,
    ChatRequest,
    ChatResponse,
    IntentType,
    SDLCStage,
    ToolCall,
    WorkflowState,
)
from orchestrator.pipeline import PipelineEngine
from orchestrator.router import AgentRouter
from orchestrator.scheduler import TaskScheduler
from orchestrator.state_manager import StateManager
from orchestrator.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Shared singletons (initialised in lifespan)
# ---------------------------------------------------------------------------
state_manager: StateManager
agent_router: AgentRouter
workflow_engine: WorkflowEngine
mcp_server: MCPServer
agent_instances: dict[str, BaseAgent]
pipeline_engine: PipelineEngine
scheduler: TaskScheduler
enhancer: EnhancedAgentOrchestrator

_AGENT_LABELS: dict[str, str] = {
    "pm_agent": "Product Manager",
    "techlead_agent": "Tech Lead",
    "scrum_agent": "Scrum Master",
    "dev_be_agent": "Backend Developer",
    "dev_fe_agent": "Frontend Developer",
    "qa_agent": "QA Engineer",
    "devops_agent": "DevOps Engineer",
}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown hook — initialise all subsystems."""
    global state_manager, agent_router, workflow_engine, mcp_server  # noqa: PLW0603
    global agent_instances, pipeline_engine, scheduler, enhancer  # noqa: PLW0603

    # --- Core systems ---
    state_manager = StateManager()
    agent_router = AgentRouter()
    workflow_engine = WorkflowEngine(state_manager)

    # --- MCP — register all tool adapters ---
    mcp_server = MCPServer()
    mcp_server.register_tool("jira", JiraTool())
    mcp_server.register_tool("github", GitHubTool())
    mcp_server.register_tool("slack", SlackTool())
    mcp_server.register_tool("calendar", CalendarTool())

    # --- Instantiate all agents ---
    agent_instances = {
        agent_id: agent_cls()
        for agent_id, agent_cls in AGENT_REGISTRY.items()
    }

    # --- Enhanced agent orchestrator (ticket-aware) ---
    enhancer = EnhancedAgentOrchestrator(agent_instances, mcp_server)

    # --- Autonomous pipeline engine ---
    pipeline_engine = PipelineEngine(agent_instances, mcp_server)

    # --- Background scheduler (daily standup, hourly updates) ---
    scheduler = TaskScheduler(mcp_server, standup_hour=17, timezone="UTC")

    logger.info(
        "Orchestrator started — %d agents, %d tools, pipeline ready, scheduler ready.",
        len(agent_instances),
        len(mcp_server.get_available_tools()),
    )
    yield
    # Graceful shutdown
    scheduler.stop()
    logger.info("Orchestrator shut down.")


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Engineering OS — Orchestrator",
    description=(
        "Central brain for the InsureOS spec-driven SDLC platform. "
        "Routes requests to AI agents, manages autonomous pipelines, "
        "executes tool calls via MCP, and runs background scheduled tasks."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================================================================
# HEALTH / READINESS
# ===================================================================

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, Any]:
    """Deep readiness — verifies all subsystems."""
    try:
        _ = state_manager.get_state()
        return {
            "status": "ready",
            "state_loaded": True,
            "agents": len(agent_instances),
            "tools": mcp_server.get_available_tools(),
            "scheduler_running": scheduler._running if hasattr(scheduler, '_running') else False,
            "active_pipelines": len([
                p for p in pipeline_engine.list_pipelines()
                if p.status.value == "running"
            ]),
        }
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        return {"status": "not_ready", "state_loaded": False}


# ===================================================================
# CHAT (single-agent, request-response)
# ===================================================================

async def _process_message(message: str, session_id: str) -> ChatResponse:
    """Route message to agent, execute tool calls, return response."""
    route_result = agent_router.route(message)
    intent = IntentType(route_result.metadata["intent"])
    target_agent_id = route_result.agent_id

    agent = agent_instances.get(target_agent_id)
    if agent is None:
        return ChatResponse(
            session_id=session_id,
            intent=intent,
            agent_id=target_agent_id,
            message=f"Error: Agent '{target_agent_id}' is not registered.",
            status=AgentStatus.FAILED,
        )

    # Use enhanced orchestrator for ticket-aware processing
    result = await enhancer.run_agent(
        agent_id=target_agent_id,
        message=message,
        context={
            "session_id": session_id,
            "intent": intent.value,
            "workflow_stage": workflow_engine.get_current_stage().value,
        },
    )

    label = _AGENT_LABELS.get(target_agent_id, target_agent_id)

    # Build response message with tool summary
    msg_parts = [f"[{label}] {result.output}"]
    if result.tool_results:
        ok = sum(1 for r in result.tool_results if r.get("success"))
        fail = len(result.tool_results) - ok
        msg_parts.append(f"\n\n--- Tool Execution ---\n{ok} succeeded, {fail} failed.")
        for r in result.tool_results:
            if not r.get("success"):
                msg_parts.append(f"  Error: {r.get('error', 'unknown')}")
    if result.needs_human:
        msg_parts.append(f"\n\n--- Human Input Needed ---\n{result.human_question}")

    if result.status == "completed":
        status = AgentStatus.COMPLETED
    elif result.status == "needs_human":
        status = AgentStatus.BLOCKED
    else:
        status = AgentStatus.FAILED

    return ChatResponse(
        session_id=session_id,
        intent=intent,
        agent_id=target_agent_id,
        message="\n".join(msg_parts),
        data={
            "agent_output": result.output,
            "tool_results": result.tool_results or None,
            "memory_updates": result.memory_updates or None,
            "jira_updates": result.jira_updates or None,
            "git_operations": result.git_operations or None,
            "errors": result.errors or None,
        },
        status=status,
    )


def _should_autostart_pipeline(message: str) -> bool:
    """Return True when the message looks like a new requirement brief.

    This enables the default "single requirement -> full SDLC pipeline" flow
    while avoiding accidental triggers for status/report style prompts.
    """
    text = message.strip()
    lower = text.lower()

    if not text or lower.startswith("/single"):
        return False

    requirement_starters = (
        "build ",
        "we need ",
        "create ",
        "develop ",
        "implement ",
    )

    looks_like_requirement_intent = agent_router.detect_intent(text) == IntentType.REQUIREMENTS
    starts_like_requirement = any(lower.startswith(s) for s in requirement_starters)
    has_structured_brief = ("where:" in lower) or ("\n- " in text) or ("\n* " in text)

    return len(text) >= 40 and (looks_like_requirement_intent or (starts_like_requirement and has_structured_brief))


async def _run_pipeline_from_chat(message: str, session_id: str) -> ChatResponse:
    """Run the autonomous pipeline and return a chat-compatible response."""
    run = await pipeline_engine.start_pipeline(message)

    if run.status.value == "completed":
        status = AgentStatus.COMPLETED
    elif run.status.value == "paused_for_human":
        status = AgentStatus.BLOCKED
    elif run.status.value == "running":
        status = AgentStatus.IN_PROGRESS
    else:
        status = AgentStatus.FAILED

    return ChatResponse(
        session_id=session_id,
        intent=IntentType.REQUIREMENTS,
        agent_id="orchestrator",
        message=(
            "[Orchestrator] Auto SDLC pipeline triggered from your requirement.\n\n"
            f"{_pipeline_summary(run)}"
        ),
        data={
            "pipeline_id": run.pipeline_id,
            "pipeline_status": run.status.value,
            "current_stage": run.current_stage,
            "jira_tickets": run.jira_tickets,
            "stages_completed": len(run.stages_log),
            "human_interventions": [
                {
                    "stage": h.stage,
                    "question": h.question,
                    "resolved": h.response is not None,
                }
                for h in run.human_interventions
            ],
        },
        status=status,
    )


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a user chat message through enhanced agent pipeline."""
    session = state_manager.get_session(request.session_id)
    session_id = session.session_id
    state_manager.append_message(session_id, role="user", content=request.message)

    if _should_autostart_pipeline(request.message):
        response = await _run_pipeline_from_chat(request.message, session_id)
    else:
        response = await _process_message(request.message, session_id)

    state_manager.append_message(
        session_id,
        role="assistant",
        content=response.message,
        metadata={"agent_id": response.agent_id, "intent": response.intent.value},
    )
    return response


# ===================================================================
# AUTONOMOUS PIPELINE (full SDLC)
# ===================================================================

class PipelineStartRequest(BaseModel):
    requirement: str


class PipelineResumeRequest(BaseModel):
    human_response: str


@app.post("/api/v1/pipeline/start")
async def start_pipeline(request: PipelineStartRequest) -> dict[str, Any]:
    """Start a full autonomous SDLC pipeline for a requirement.

    This kicks off the entire flow:
    PM → TechLead → Scrum → Dev (BE+FE) → QA → DevOps

    The pipeline runs autonomously, creating Jira tickets, branches,
    code, tests, and deployments. If it hits a blocker, it pauses
    and requests human intervention.
    """
    run = await pipeline_engine.start_pipeline(request.requirement)
    return {
        "pipeline_id": run.pipeline_id,
        "status": run.status.value,
        "current_stage": run.current_stage,
        "requirement": run.requirement,
        "stages_completed": len(run.stages_log),
        "jira_tickets": run.jira_tickets,
        "needs_human": any(h.response is None for h in run.human_interventions),
        "message": _pipeline_summary(run),
    }


@app.get("/api/v1/pipeline/{pipeline_id}")
async def get_pipeline(pipeline_id: str) -> dict[str, Any]:
    """Get the current status of a pipeline run."""
    run = pipeline_engine.get_pipeline_status(pipeline_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found.")
    return {
        "pipeline_id": run.pipeline_id,
        "status": run.status.value,
        "current_stage": run.current_stage,
        "requirement": run.requirement,
        "stages": [
            {
                "stage": s.stage,
                "agent_id": s.agent_id,
                "status": s.status,
                "output_summary": str(s.output)[:200] if s.output else None,
                "tool_calls_count": len(s.tool_calls_executed),
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in run.stages_log
        ],
        "jira_tickets": run.jira_tickets,
        "human_interventions": [
            {
                "stage": h.stage,
                "question": h.question,
                "resolved": h.response is not None,
            }
            for h in run.human_interventions
        ],
    }


@app.post("/api/v1/pipeline/{pipeline_id}/resume")
async def resume_pipeline(pipeline_id: str, request: PipelineResumeRequest) -> dict[str, Any]:
    """Resume a paused pipeline with human response."""
    run = pipeline_engine.get_pipeline_status(pipeline_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found.")
    if run.status.value != "paused_for_human":
        raise HTTPException(status_code=400, detail="Pipeline is not paused for human input.")

    updated = await pipeline_engine.resume_pipeline(pipeline_id, request.human_response)
    return {
        "pipeline_id": updated.pipeline_id,
        "status": updated.status.value,
        "current_stage": updated.current_stage,
        "message": _pipeline_summary(updated),
    }


@app.get("/api/v1/pipeline")
async def list_pipelines() -> list[dict[str, Any]]:
    """List all pipeline runs."""
    return [
        {
            "pipeline_id": r.pipeline_id,
            "status": r.status.value,
            "current_stage": r.current_stage,
            "requirement": r.requirement[:100],
            "jira_tickets_count": len(r.jira_tickets),
            "stages_completed": len(r.stages_log),
        }
        for r in pipeline_engine.list_pipelines()
    ]


def _pipeline_summary(run: Any) -> str:
    """Build a human-readable summary of a pipeline run."""
    lines = [f"Pipeline {run.pipeline_id[:8]}... — {run.status.value}"]
    lines.append(f"Requirement: {run.requirement[:100]}")
    if run.jira_tickets:
        lines.append(f"Jira tickets: {', '.join(run.jira_tickets)}")
    for s in run.stages_log:
        st = s.status.value if hasattr(s.status, 'value') else str(s.status)
        icon = {"completed": "done", "failed": "FAIL", "in_progress": ">>>"}.get(st, "...")
        lines.append(f"  [{icon}] {s.stage} ({s.agent_id}): {(s.output or '')[:80]}")
    pending_human = [h for h in run.human_interventions if not h.resolved]
    if pending_human:
        lines.append(f"\nAWAITING HUMAN INPUT: {pending_human[0].question}")
    return "\n".join(lines)


# ===================================================================
# SCHEDULER (daily standup, hourly updates)
# ===================================================================

@app.post("/api/v1/scheduler/start")
async def start_scheduler() -> dict[str, str]:
    """Start the background scheduler for automated Slack updates."""
    scheduler.start()
    return {"status": "started", "message": "Scheduler running: daily standup + hourly updates + pipeline health checks"}


@app.post("/api/v1/scheduler/stop")
async def stop_scheduler() -> dict[str, str]:
    """Stop the background scheduler."""
    scheduler.stop()
    return {"status": "stopped"}


@app.get("/api/v1/scheduler")
async def get_scheduler_status() -> dict[str, Any]:
    """Get scheduler status and next run times."""
    return scheduler.get_schedule()


@app.post("/api/v1/scheduler/standup")
async def trigger_standup() -> dict[str, str]:
    """Manually trigger a daily standup notification on Slack."""
    await scheduler.run_standup()
    return {"status": "ok", "message": "Standup notification sent to Slack"}


@app.post("/api/v1/scheduler/status-update")
async def trigger_status_update() -> dict[str, str]:
    """Manually trigger an hourly ticket status update on Slack."""
    await scheduler.run_status_update()
    return {"status": "ok", "message": "Status update sent to Slack"}


# ===================================================================
# WORKFLOW
# ===================================================================

@app.get("/api/v1/workflow", response_model=WorkflowState)
async def get_workflow() -> WorkflowState:
    return workflow_engine.get_workflow_state()


@app.post("/api/v1/workflow/advance")
async def advance_workflow() -> dict[str, Any]:
    if not workflow_engine.can_advance():
        current = workflow_engine.get_current_stage()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot advance from '{current.value}' — exit criteria not met.",
        )
    new_state = workflow_engine.advance_stage()
    return {
        "status": "advanced",
        "previous_stage": new_state.stages_completed[-1].value if new_state.stages_completed else None,
        "current_stage": new_state.current_stage.value,
    }


class CriterionRequest(BaseModel):
    stage: str
    criterion: str


@app.post("/api/v1/workflow/complete-criterion")
async def complete_criterion(request: CriterionRequest) -> dict[str, str]:
    try:
        stage = SDLCStage(request.stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {request.stage}")
    workflow_engine.complete_criterion(stage, request.criterion)
    return {"status": "ok", "stage": request.stage, "criterion": request.criterion}


# ===================================================================
# AGENTS
# ===================================================================

@app.get("/api/v1/agents")
async def list_agents() -> list[dict[str, Any]]:
    return [
        {
            "agent_id": agent.agent_id,
            "role": agent.role,
            "label": _AGENT_LABELS.get(agent.agent_id, agent.role),
            "permissions": agent.permissions,
        }
        for agent in agent_instances.values()
    ]


# ===================================================================
# DIRECT TOOL EXECUTION
# ===================================================================

class ToolExecuteRequest(BaseModel):
    agent_id: str
    tool: str
    input: dict[str, Any] = {}


@app.post("/api/v1/tools/execute")
async def execute_tool(request: ToolExecuteRequest) -> dict[str, Any]:
    tool_call = {"type": "tool_call", "tool": request.tool, "input": request.input}
    return await mcp_server.execute(tool_call, agent_id=request.agent_id)


# ===================================================================
# WEBSOCKET
# ===================================================================

@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket) -> None:
    """Real-time streaming chat over WebSocket."""
    await ws.accept()
    session_id = str(uuid.uuid4())
    logger.info("WebSocket session opened: %s", session_id)

    try:
        while True:
            data = await ws.receive_json()
            message: str = data.get("message", "")
            sid: str = data.get("session_id") or session_id

            if not message.strip():
                await ws.send_json({"error": "Empty message."})
                continue

            state_manager.append_message(sid, role="user", content=message)
            response = await _process_message(message, sid)
            state_manager.append_message(
                sid,
                role="assistant",
                content=response.message,
                metadata={"agent_id": response.agent_id, "intent": response.intent.value},
            )
            await ws.send_json(response.model_dump(mode="json"))
    except WebSocketDisconnect:
        logger.info("WebSocket session closed: %s", session_id)
    except Exception:
        logger.exception("WebSocket error in session %s", session_id)
        await ws.close(code=1011)
