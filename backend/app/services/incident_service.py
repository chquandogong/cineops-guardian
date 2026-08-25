from collections.abc import AsyncGenerator

from backend.app.agents.orchestrator import AgentOrchestrator
from backend.app.agents.state_machine import InvestigationStateMachine
from backend.app.domain.mock_data import get_mock_incident
from backend.app.domain.models import Incident, ToolTraceEntry
from backend.app.services.recovery_service import RecoveryService


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
        self._current_incident = get_mock_incident()
        self._current_incident.tool_trace = []
        state_machine = InvestigationStateMachine(self._current_incident)

        async for trace_entry in state_machine.stream_investigation():
            self._current_incident.tool_trace.append(trace_entry)
            yield trace_entry

    async def approve_recovery(self, action_id: str, operator_name: str) -> Incident:
        self._current_incident = await self.recovery_service.execute_recovery(
            self._current_incident, action_id, operator_name
        )
        return self._current_incident


incident_service = IncidentService()
