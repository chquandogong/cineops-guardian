import logging
from collections.abc import AsyncGenerator

from backend.app.agents.mcp_agent import MCPGeminiAgent
from backend.app.agents.orchestrator import AgentOrchestrator
from backend.app.agents.state_machine import InvestigationStateMachine
from backend.app.domain.mock_data import get_mock_incident
from backend.app.domain.models import Incident, ToolTraceEntry
from backend.app.mcp.router import MCPUnavailableError
from backend.app.services.recovery_service import RecoveryService
from backend.app.settings import settings

logger = logging.getLogger(__name__)


class IncidentService:
    """Manages active incidents, investigation lifecycle, and recovery operations."""

    def __init__(self):
        self._current_incident: Incident = get_mock_incident()
        self.orchestrator = AgentOrchestrator()
        self.recovery_service = RecoveryService()

    def get_current_incident(self) -> Incident:
        return self._current_incident

    def reset_incident(self) -> Incident:
        self._current_incident = get_mock_incident()
        return self._current_incident

    async def run_investigation(self) -> Incident:
        self._current_incident = await self.orchestrator.investigate_incident(
            self._current_incident.incident_id
        )
        return self._current_incident

    async def stream_investigation_trace(self) -> AsyncGenerator[ToolTraceEntry, None]:
        """Streams the investigation step by step for the console's live trace.

        In ``real`` mode this is the MCP agent itself: each entry appears the moment
        Gemini picks a tool and the MCP server answers, so the operator watches the
        agent decide. If no MCP server is reachable, or the agent fails, the
        deterministic state machine takes over mid-stream so the console still
        completes an investigation.
        """
        incident = get_mock_incident()
        incident.tool_trace = []
        self._current_incident = incident

        if settings.DEMO_MODE == "real":
            agent = MCPGeminiAgent(incident)
            try:
                async for entry in agent.stream():
                    incident.tool_trace.append(entry)
                    yield entry
                if agent.verdict is not None:
                    AgentOrchestrator.apply_verdict(incident, agent.verdict)
                    incident.status = "awaiting_approval"
                    return
                logger.warning("Agent produced no verdict; replaying fixture diagnosis")
            except MCPUnavailableError as e:
                logger.warning("No MCP server reachable (%s); streaming deterministic trace", e)
            except Exception as e:  # noqa: BLE001 - never break the operator's console
                logger.warning(
                    "MCP agent stream failed (%s: %s); streaming deterministic trace",
                    type(e).__name__,
                    e,
                )

        offset = len(incident.tool_trace)
        state_machine = InvestigationStateMachine(incident)
        async for entry in state_machine.stream_investigation():
            entry.step_number += offset
            incident.tool_trace.append(entry)
            yield entry
        incident.status = "awaiting_approval"

    async def approve_recovery(self, action_id: str, operator_name: str) -> Incident:
        self._current_incident = await self.recovery_service.execute_recovery(
            self._current_incident, action_id, operator_name
        )
        return self._current_incident


incident_service = IncidentService()
