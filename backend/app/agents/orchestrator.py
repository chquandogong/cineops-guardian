import logging

from backend.app.agents.mcp_agent import MCPGeminiAgent
from backend.app.agents.schemas import AgentInvestigationOutput
from backend.app.agents.state_machine import InvestigationStateMachine
from backend.app.domain.mock_data import get_mock_incident
from backend.app.domain.models import Hypothesis, Incident, RecoveryRecommendation
from backend.app.mcp.router import MCPUnavailableError
from backend.app.settings import settings

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Coordinates the investigation.

    In ``real`` mode the work is done by :class:`MCPGeminiAgent`: Gemini decides
    which MCP tools to call and its structured verdict becomes the incident's
    diagnosis. In ``mock`` mode — and if the agent cannot reach its MCP servers or
    fails to produce a parseable verdict — the deterministic state machine and the
    recorded fixture take over, so an offline demo stays reproducible.
    """

    def __init__(self):
        self.mode = settings.DEMO_MODE
        self.model_name = settings.GEMINI_MODEL

    async def investigate_incident(self, incident_id: str = "inc-stage-a-001") -> Incident:
        incident = get_mock_incident()

        if self.mode == "real":
            try:
                agent = MCPGeminiAgent(incident)
                traces, verdict = await agent.run()
                incident.tool_trace = traces
                if verdict is not None:
                    self._apply_verdict(incident, verdict)
                    incident.status = "awaiting_approval"
                    return incident
                logger.warning("Agent produced no verdict; using recorded fixture diagnosis")
            except MCPUnavailableError as e:
                logger.warning("No MCP server reachable (%s); using deterministic fallback", e)
            except Exception as e:  # noqa: BLE001 - never 500 a live stage console
                logger.warning(
                    "MCP agent failed (%s: %s); using deterministic fallback", type(e).__name__, e
                )

        state_machine = InvestigationStateMachine(incident)
        traces = []
        async for trace_entry in state_machine.stream_investigation():
            traces.append(trace_entry)
        incident.tool_trace = traces
        incident.status = "awaiting_approval"
        return incident

    @staticmethod
    def _apply_verdict(incident: Incident, verdict: AgentInvestigationOutput) -> None:
        """Replaces the fixture diagnosis with what the agent actually concluded."""
        ordered = [verdict.primary_hypothesis, *verdict.alternative_hypotheses]
        incident.hypotheses = [
            Hypothesis(
                id=f"hyp-{index}",
                title=h.title,
                rank=h.rank or index,
                confidence=h.confidence,
                status=h.status,
                rationale=h.rationale,
                supporting_evidence=h.supporting_evidence,
                conflicting_evidence=h.conflicting_evidence,
                missing_evidence=h.missing_evidence,
            )
            for index, h in enumerate(ordered, start=1)
        ]
        if verdict.recommendations:
            incident.recommendations = [
                RecoveryRecommendation(
                    action_id=r.action_id,
                    title=r.title,
                    action_description=r.action_description,
                    risk_level=r.risk_level,
                    requires_approval=True,
                    expected_effect=r.expected_effect,
                    rollback_instructions=r.rollback_instructions,
                    success_criteria=r.success_criteria,
                )
                for r in verdict.recommendations
            ]
        incident.production_impact.estimated_delay_minutes = verdict.production_delay_minutes
        incident.resolution_summary = verdict.root_cause_summary
