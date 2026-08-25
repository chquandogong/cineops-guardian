import pytest

from backend.app.integrations.grafana.mcp_client import GrafanaMCPClient


@pytest.mark.asyncio
async def test_grafana_mcp_query():
    client = GrafanaMCPClient()
    alerts = await client.get_alert_rules("stage-a")
    assert len(alerts) >= 2
    assert any(a["name"] == "CameraDollyOscillation" for a in alerts)

    prom_res = await client.query_prometheus("rate(nav_recovery_loop_count[1m])")
    assert prom_res["status"] == "success"

    logs = await client.query_loki('{stage="stage-a"}')
    assert len(logs) >= 4
    assert any("checksum mismatch" in log_item["line"] for log_item in logs)
