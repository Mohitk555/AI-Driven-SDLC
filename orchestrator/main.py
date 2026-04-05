"""FastAPI application — the orchestrator's HTTP / WebSocket entry point.

Endpoints
---------
GET  /health              — shallow health check
GET  /ready               — deep readiness check
POST /api/v1/chat         — synchronous chat (accepts ChatRequest, returns ChatResponse)
WS   /ws/chat             — streaming chat over WebSocket
GET  /api/v1/workflow      — current SDLC workflow state
POST /api/v1/workflow/advance — advance SDLC to next stage
GET  /api/v1/agents        — list all registered agents
POST /api/v1/tools/execute — manually execute a tool call via MCP
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
from orchestrator.models import (
    AgentResponse,
    AgentStatus,
    ChatRequest,
    ChatResponse,
    IntentType,
    ToolCall,
    WorkflowState,
)
from orchestrator.router import AgentRouter
from orchestrator.state_manager import StateManager
from orchestrator.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared singletons (initialised in lifespan)
# ---------------------------------------------------------------------------
state_manager: StateManager
agent_router: AgentRouter
workflow_engine: WorkflowEngine
mcp_server: MCPServer
agent_instances: dict[str, BaseAgent]

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
    """Startup / shutdown hook — initialise shared objects."""
    global state_manager, agent_router, workflow_engine, mcp_server, agent_instances  # noqa: PLW0603

    # Core systems
    state_manager = StateManager()
    agent_router = AgentRouter()
    workflow_engine = WorkflowEngine(state_manager)

    # MCP — register all tool adapters
    mcp_server = MCPServer()
    mcp_server.register_tool("jira", JiraTool())
    mcp_server.register_tool("github", GitHubTool())
    mcp_server.register_tool("slack", SlackTool())
    mcp_server.register_tool("calendar", CalendarTool())

    # Instantiate one instance of each agent
    agent_instances = {
        agent_id: agent_cls()
        for agent_id, agent_cls in AGENT_REGISTRY.items()
    }

    logger.info(
        "Orchestrator started — %d agents registered, %d tools available.",
        len(agent_instances),
        len(mcp_server.get_available_tools()),
    )
    yield
    logger.info("Orchestrator shutting down.")


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Engineering OS — Orchestrator",
    description="Central brain for the InsureOS spec-driven SDLC platform.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten per-environment in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health / readiness (constitution §11)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str | bool]:
    """Deep readiness — verifies that critical subsystems are initialised."""
    try:
        _ = state_manager.get_state()
        return {"status": "ready", "state_loaded": True}
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        return {"status": "not_ready", "state_loaded": False}


# ---------------------------------------------------------------------------
# Core orchestration logic
# ---------------------------------------------------------------------------

async def _process_message(message: str, session_id: str) -> ChatResponse:
    """Shared processing pipeline for both REST and WebSocket.

    Flow:
    1. Detect intent and route to agent.
    2. Invoke the real agent's process() method.
    3. Execute any tool calls the agent returns via MCP.
    4. Build and return ChatResponse.
    """
    # 1. Route
    route_result = agent_router.route(message)
    intent = IntentType(route_result.metadata["intent"])
    target_agent_id = route_result.agent_id

    # 2. Get agent instance and invoke
    agent = agent_instances.get(target_agent_id)
    if agent is None:
        logger.error("No agent instance for %s", target_agent_id)
        return ChatResponse(
            session_id=session_id,
            intent=intent,
            agent_id=target_agent_id,
            message=f"Error: Agent '{target_agent_id}' is not registered.",
            status=AgentStatus.FAILED,
        )

    context: dict[str, Any] = {
        "session_id": session_id,
        "intent": intent.value,
        "workflow_stage": workflow_engine.get_current_stage().value,
    }

    agent_response: AgentResponse = await agent.process(message, context)

    # 3. Execute tool calls through MCP (if any)
    tool_results: list[dict[str, Any]] = []
    for tc in agent_response.tool_calls:
        tool_call_dict = tc.model_dump() if isinstance(tc, ToolCall) else tc
        result = await mcp_server.execute(tool_call_dict, agent_id=target_agent_id)
        tool_results.append(result)
        logger.info(
            "MCP executed %s for %s — success=%s",
            tc.tool if isinstance(tc, ToolCall) else tc.get("tool"),
            target_agent_id,
            result.get("success"),
        )

    # 4. Build human-readable message
    label = _AGENT_LABELS.get(target_agent_id, target_agent_id)
    output_text = agent_response.output if isinstance(agent_response.output, str) else str(agent_response.output)

    # Append tool execution summary if tools were called
    tool_summary = ""
    if tool_results:
        executed = [r for r in tool_results if r.get("success")]
        failed = [r for r in tool_results if not r.get("success")]
        tool_summary = f"\n\n--- Tool Execution ---\nExecuted: {len(executed)} succeeded, {len(failed)} failed."
        for r in failed:
            tool_summary += f"\n  Error: {r.get('error', 'unknown')}"

    final_message = f"[{label}] {output_text}{tool_summary}"

    return ChatResponse(
        session_id=session_id,
        intent=intent,
        agent_id=target_agent_id,
        message=final_message,
        data={
            "agent_output": agent_response.output,
            "tool_results": tool_results if tool_results else None,
            "metadata": agent_response.metadata,
        },
        tool_calls=agent_response.tool_calls,
        status=agent_response.status,
    )


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a user chat message through the full agent pipeline."""
    # Session management
    session = state_manager.get_session(request.session_id)
    session_id = session.session_id
    state_manager.append_message(session_id, role="user", content=request.message)

    # Process through agents
    response = await _process_message(request.message, session_id)

    # Persist assistant response
    state_manager.append_message(
        session_id,
        role="assistant",
        content=response.message,
        metadata={"agent_id": response.agent_id, "intent": response.intent.value},
    )

    return response


# ---------------------------------------------------------------------------
# Workflow endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/workflow", response_model=WorkflowState)
async def get_workflow() -> WorkflowState:
    return workflow_engine.get_workflow_state()


@app.post("/api/v1/workflow/advance")
async def advance_workflow() -> dict[str, Any]:
    """Attempt to advance the SDLC workflow to the next stage."""
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
    """Mark an exit criterion as completed for a given stage."""
    from orchestrator.models import SDLCStage
    try:
        stage = SDLCStage(request.stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {request.stage}")
    workflow_engine.complete_criterion(stage, request.criterion)
    return {"status": "ok", "stage": request.stage, "criterion": request.criterion}


# ---------------------------------------------------------------------------
# Agent info endpoint
# ---------------------------------------------------------------------------

@app.get("/api/v1/agents")
async def list_agents() -> list[dict[str, Any]]:
    """List all registered agents and their metadata."""
    return [
        {
            "agent_id": agent.agent_id,
            "role": agent.role,
            "label": _AGENT_LABELS.get(agent.agent_id, agent.role),
            "permissions": agent.permissions,
        }
        for agent in agent_instances.values()
    ]


# ---------------------------------------------------------------------------
# Direct tool execution endpoint
# ---------------------------------------------------------------------------

class ToolExecuteRequest(BaseModel):
    agent_id: str
    tool: str
    input: dict[str, Any] = {}


@app.post("/api/v1/tools/execute")
async def execute_tool(request: ToolExecuteRequest) -> dict[str, Any]:
    """Execute a tool call directly via MCP (for testing/admin)."""
    tool_call = {"type": "tool_call", "tool": request.tool, "input": request.input}
    result = await mcp_server.execute(tool_call, agent_id=request.agent_id)
    return result


# ---------------------------------------------------------------------------
# WebSocket streaming chat
# ---------------------------------------------------------------------------

@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket) -> None:
    """Real-time streaming chat over WebSocket.

    Protocol (JSON messages):
      Client → Server:  { "message": "...", "session_id": "..." | null }
      Server → Client:  ChatResponse-shaped JSON
    """
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
