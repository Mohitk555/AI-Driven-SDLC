"""Pydantic v2 models for the orchestrator layer.

Defines the data contracts for chat, agent responses, tool calls,
workflow state, and session management.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SDLCStage(str, enum.Enum):
    """Ordered stages of the software-development lifecycle."""

    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    TASK_PLANNING = "task_planning"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class AgentStatus(str, enum.Enum):
    """Status codes an agent may report."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class IntentType(str, enum.Enum):
    """High-level intent categories detected from user messages."""

    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    TASK_PLANNING = "task_planning"
    DEV_BACKEND = "dev_backend"
    DEV_FRONTEND = "dev_frontend"
    QA = "qa"
    DEVOPS = "devops"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# Tool-call models (constitution §12)
# ---------------------------------------------------------------------------

class ToolCall(BaseModel):
    """A request from an agent to invoke an external tool."""

    type: str = "tool_call"
    tool: str = Field(..., description="Tool identifier in <service>.<action> format")
    input: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """The result returned after executing a tool call."""

    tool: str
    success: bool
    output: Any = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Agent response (constitution §12)
# ---------------------------------------------------------------------------

class AgentResponse(BaseModel):
    """Structured response every agent must return."""

    agent_id: str
    status: AgentStatus
    output: Any
    tool_calls: list[ToolCall] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Chat models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Incoming chat message from the client."""

    message: str = Field(..., min_length=1, max_length=4096)
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Response returned to the client after processing a chat message."""

    session_id: str
    intent: IntentType
    agent_id: str
    message: str
    data: Any = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    status: AgentStatus = AgentStatus.COMPLETED
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Workflow / session state
# ---------------------------------------------------------------------------

class StageCriteria(BaseModel):
    """Entry and exit criteria for a single SDLC stage."""

    entry: list[str] = Field(default_factory=list)
    exit: list[str] = Field(default_factory=list)


class WorkflowState(BaseModel):
    """Persisted state of the SDLC workflow pipeline."""

    current_stage: SDLCStage = SDLCStage.REQUIREMENTS
    stages_completed: list[SDLCStage] = Field(default_factory=list)
    stage_criteria: dict[str, StageCriteria] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SessionState(BaseModel):
    """State for a single user/chat session."""

    session_id: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    active_agents: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SystemState(BaseModel):
    """Top-level persisted system state."""

    workflow: WorkflowState = Field(default_factory=WorkflowState)
    sessions: dict[str, SessionState] = Field(default_factory=dict)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
