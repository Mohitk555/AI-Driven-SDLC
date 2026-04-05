"""AI Engineering OS — Agent implementations.

This package contains all SDLC agent classes.  Import them from here::

    from agents import PMAgent, ScrumAgent, TechLeadAgent, ...
"""

from .base_agent import BaseAgent
from .dev_be_agent import DevBackendAgent
from .dev_fe_agent import DevFrontendAgent
from .devops_agent import DevOpsAgent
from .pm_agent import PMAgent
from .qa_agent import QAAgent
from .scrum_agent import ScrumAgent
from .techlead_agent import TechLeadAgent

__all__ = [
    "BaseAgent",
    "DevBackendAgent",
    "DevFrontendAgent",
    "DevOpsAgent",
    "PMAgent",
    "QAAgent",
    "ScrumAgent",
    "TechLeadAgent",
]

# Registry mapping agent_id -> class for dynamic lookup by the orchestrator.
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    _cls.agent_id: _cls
    for _cls in (PMAgent, ScrumAgent, TechLeadAgent, DevBackendAgent, DevFrontendAgent, QAAgent, DevOpsAgent)
}
