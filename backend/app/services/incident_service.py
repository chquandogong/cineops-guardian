import logging
from collections.abc import AsyncGenerator

from backend.app.agents.mcp_agent import MCPGeminiAgent
from backend.app.agents.orchestrator import AgentOrchestrator
from backend.app.agents.state_machine import InvestigationStateMachine
from backend.app.domain.mock_data import get_mock_incident
from backend.app.domain.models import Incident, ToolTraceEntry
from backend.app.mcp.router import MCPUnavailableError
from backend.app.services.incident_store import build_incident_store
from backend.app.services.recovery_service import RecoveryService
from backend.app.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_INCIDENT_ID = "inc-stage-a-001"


class IncidentService:
    """Manages active incidents, investigation lifecycle, and recovery operations.

    State lives in an :mod:`incident_store` rather than on this object, so a
    console polling ``/incidents/current`` sees the same incident regardless of
    which instance answers it.
    """

    def __init__(self):
        self.store = build_incident_store()
        self.orchestrator = AgentOrchestrator()
        self.recovery_service = RecoveryService()

    @property
    def state_backend(self) -> str:
        return self.store.backend

    async def get_current_incident(self) -> Incident:
        return await self.store.load(DEFAULT_INCIDENT_ID)

    async def reset_incident(self) -> Incident:
        incident = get_mock_incident()
        await self.store.save(incident)
        return incident

    async def run_investigation(self) -> Incident:
        current = await self.store.load(DEFAULT_INCIDENT_ID)
        incident = await self.orchestrator.investigate_incident(current.incident_id)
        await self.store.save(incident)
        return incident

    async def stream_investigation_trace(self) -> AsyncGenerator[ToolTraceEntry, None]:
        """Streams the investigation step by step for the console's live trace.

        In ``real`` mode this is the MCP agent itself: each entry appears the moment
        Gemini picks a tool and the MCP server answers, so the operator watches the
        agent decide. Each entry is also persisted, so a reader on another instance
        sees the investigation progress rather than a stale snapshot. If no MCP
        server is reachable, or the agent fails, the deterministic state machine
        takes over mid-stream so the console still completes an investigation.
        """
        incident = get_mock_incident()
        incident.tool_trace = []
        await self.store.save(incident)

        if settings.DEMO_MODE == "real":
            agent = MCPGeminiAgent(incident)
            try:
                async for entry in agent.stream():
                    incident.tool_trace.append(entry)
                    await self.store.save(incident)
                    yield entry
                if agent.verdict is not None:
                    AgentOrchestrator.apply_verdict(incident, agent.verdict)
                    incident.status = "awaiting_approval"
                    await self.store.save(incident)
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
            await self.store.save(incident)
            yield entry
        incident.status = "awaiting_approval"
        await self.store.save(incident)

    async def approve_recovery(self, action_id: str, operator_name: str) -> Incident:
        current = await self.store.load(DEFAULT_INCIDENT_ID)
        incident = await self.recovery_service.execute_recovery(current, action_id, operator_name)
        await self.store.save(incident)
        return incident


incident_service = IncidentService()
