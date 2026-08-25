import pytest

from backend.app.agents.state_machine import InvestigationStateMachine
from backend.app.domain.mock_data import get_mock_incident


@pytest.mark.asyncio
async def test_state_machine_steps():
    sm = InvestigationStateMachine(get_mock_incident())
    traces = []
    async for entry in sm.stream_investigation():
        traces.append(entry)

    assert len(traces) == 11
    assert traces[0].step_name == "incident_intake"
    assert traces[1].step_name == "collect_grafana_context"
    assert traces[2].step_name == "collect_grafana_logs"
    assert traces[5].step_name == "query_historical_incidents"
    assert traces[6].step_name == "inspect_recording_evidence"
    assert traces[8].step_name == "recommend_recovery"
    assert traces[9].step_name == "request_human_approval"
    assert traces[10].step_name == "generate_incident_summary"
