"""Thread-safe system state management with JSON persistence.

The StateManager is the single source of truth for workflow progress,
session history, and project metadata.  All mutations are protected
by a re-entrant lock so the object is safe to share across threads
(e.g. when used behind FastAPI's thread-pool executor).
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from orchestrator.models import (
    SessionState,
    SystemState,
    WorkflowState,
)

logger = logging.getLogger(__name__)

_DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "memory" / "system_state.json"


class StateManager:
    """Manages and persists orchestrator state to a JSON file."""

    def __init__(self, state_path: Path | None = None) -> None:
        self._path = state_path or _DEFAULT_STATE_PATH
        self._lock = threading.RLock()
        self._state = self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> SystemState:
        """Load state from disk, returning fresh state if missing/corrupt."""
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                return SystemState.model_validate(raw)
            except (json.JSONDecodeError, ValueError):
                logger.warning("Corrupt state file at %s — starting fresh.", self._path)
        return SystemState()

    def _persist(self) -> None:
        """Write current state to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._state.updated_at = datetime.utcnow()
        self._path.write_text(
            self._state.model_dump_json(indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Public API — general state
    # ------------------------------------------------------------------

    def get_state(self) -> SystemState:
        with self._lock:
            return self._state.model_copy(deep=True)

    def update_state(self, **kwargs: Any) -> SystemState:
        """Merge top-level fields into state, persist, and return copy."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)
                else:
                    logger.warning("Ignoring unknown state field: %s", key)
            self._persist()
            return self._state.model_copy(deep=True)

    # ------------------------------------------------------------------
    # Workflow helpers
    # ------------------------------------------------------------------

    def get_workflow(self) -> WorkflowState:
        with self._lock:
            return self._state.workflow.model_copy(deep=True)

    def update_workflow(self, workflow: WorkflowState) -> None:
        with self._lock:
            self._state.workflow = workflow
            self._persist()

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    def get_session(self, session_id: str | None = None) -> SessionState:
        """Return an existing session or create a new one."""
        with self._lock:
            sid = session_id or str(uuid.uuid4())
            if sid not in self._state.sessions:
                self._state.sessions[sid] = SessionState(session_id=sid)
                self._persist()
            return self._state.sessions[sid].model_copy(deep=True)

    def save_session(self, session: SessionState) -> None:
        with self._lock:
            session.updated_at = datetime.utcnow()
            self._state.sessions[session.session_id] = session
            self._persist()

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append a chat message to the session's history."""
        with self._lock:
            session = self._state.sessions.get(session_id)
            if session is None:
                session = SessionState(session_id=session_id)
                self._state.sessions[session_id] = session
            session.messages.append(
                {
                    "role": role,
                    "content": content,
                    "metadata": metadata or {},
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            session.updated_at = datetime.utcnow()
            self._persist()

    # ------------------------------------------------------------------
    # Project metadata
    # ------------------------------------------------------------------

    def get_project_metadata(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state.project_metadata)

    def update_project_metadata(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._state.project_metadata.update(data)
            self._persist()
