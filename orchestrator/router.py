"""Intent detection and agent routing.

The AgentRouter inspects an incoming user message, classifies it into
an IntentType, and returns a lightweight AgentResponse stub that tells
the orchestrator which agent should handle the request.

Intent detection is keyword/pattern-based for now — deliberately simple
but designed so a model-based classifier can be swapped in later.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from orchestrator.models import (
    AgentResponse,
    AgentStatus,
    IntentType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pattern table — order matters: first match wins
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: list[tuple[IntentType, re.Pattern[str]]] = [
    (
        IntentType.REQUIREMENTS,
        re.compile(
            r"\b(requirement|feature|user\s*stor|stakeholder|need|scope|prd|product\s*requirement|epic|acceptance\s*criter)\b",
            re.IGNORECASE,
        ),
    ),
    (
        IntentType.ARCHITECTURE,
        re.compile(
            r"\b(architec\w+|system\s*design|database\s*design|schema\s*design|erd|tech\s*stack|data\s*model|microservice|api\s*design|api\s*contract|design\s*document)\b",
            re.IGNORECASE,
        ),
    ),
    (
        IntentType.TASK_PLANNING,
        re.compile(
            r"\b(sprint|status|ticket|jira|backlog|kanban|velocity|standup|stand-up|plan|task|story\s*point)\b",
            re.IGNORECASE,
        ),
    ),
    (
        IntentType.QA,
        re.compile(
            r"\b(tests?|qa\b|bug|validate|quality|coverage|regression|e2e|unit\s*tests?|integration\s*tests?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        IntentType.DEVOPS,
        re.compile(
            r"\b(deploy|ci\b|cd\b|ci/cd|docker|pipeline|kubernetes|k8s|terraform|helm|monitor|infra\s*as\s*code)\b",
            re.IGNORECASE,
        ),
    ),
    # Dev-frontend must come before generic dev so "react component" is not
    # swallowed by the backend pattern.
    (
        IntentType.DEV_FRONTEND,
        re.compile(
            r"\b(frontend|front-end|react|next\.?js|component|ui\b|ux\b|css|tailwind|page|layout|dashboard)\b",
            re.IGNORECASE,
        ),
    ),
    (
        IntentType.DEV_BACKEND,
        re.compile(
            r"\b(build|code|implement|develop|backend|back-end|endpoint|service|model|migration|fastapi|crud|api\b|database|schema)\b",
            re.IGNORECASE,
        ),
    ),
]

# Mapping from intent to the canonical agent that handles it.
_INTENT_TO_AGENT: dict[IntentType, str] = {
    IntentType.REQUIREMENTS: "pm_agent",
    IntentType.ARCHITECTURE: "techlead_agent",
    IntentType.TASK_PLANNING: "scrum_agent",
    IntentType.DEV_BACKEND: "dev_be_agent",
    IntentType.DEV_FRONTEND: "dev_fe_agent",
    IntentType.QA: "qa_agent",
    IntentType.DEVOPS: "devops_agent",
    IntentType.GENERAL: "pm_agent",  # fallback
}


class AgentRouter:
    """Detect user intent and route to the appropriate agent."""

    def __init__(self) -> None:
        self._patterns = _INTENT_PATTERNS
        self._agent_map = dict(_INTENT_TO_AGENT)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, message: str) -> AgentResponse:
        """Classify *message* and return a routing stub response.

        The caller (orchestrator main loop) is responsible for actually
        invoking the target agent.  This method only determines *which*
        agent to call and extracts minimal context.
        """
        intent = self._detect_intent(message)
        agent_id = self._agent_map[intent]

        logger.info("Routed message to %s (intent=%s)", agent_id, intent.value)

        return AgentResponse(
            agent_id=agent_id,
            status=AgentStatus.IN_PROGRESS,
            output=None,
            metadata={
                "intent": intent.value,
                "original_message": message,
                "routed_at": datetime.utcnow().isoformat(),
            },
        )

    def detect_intent(self, message: str) -> IntentType:
        """Public wrapper so callers can inspect intent without routing."""
        return self._detect_intent(message)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _detect_intent(self, message: str) -> IntentType:
        for intent, pattern in self._patterns:
            if pattern.search(message):
                return intent
        return IntentType.GENERAL

    def _resolve_agent(self, intent: IntentType) -> str:
        return self._agent_map.get(intent, "pm_agent")
