import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "CineOps Guardian"


@pytest.mark.asyncio
async def test_get_current_incident(client: AsyncClient):
    response = await client.get("/api/v1/incidents/current")
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "inc-stage-a-001"
    assert data["severity"] == "P1-CRITICAL"
    assert len(data["hypotheses"]) >= 3
    assert len(data["recommendations"]) >= 1


@pytest.mark.asyncio
async def test_approve_recovery_workflow(client: AsyncClient):
    # Reset first
    await client.post("/api/v1/incidents/reset")

    # Approve recovery
    response = await client.post(
        "/api/v1/incidents/approve-recovery",
        json={"action_id": "act-rec-001", "operator_name": "Lead Camera Operator"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["robot_telemetry"]["camera_fps"] == 24.0
    assert data["robot_telemetry"]["nav_recovery_loop_count"] == 0
    assert data["resolution_summary"] is not None


@pytest.mark.asyncio
async def test_api_status(client: AsyncClient):
    response = await client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["project"] == "CineOps Guardian"


@pytest.mark.asyncio
async def test_reset_incident(client: AsyncClient):
    response = await client.post("/api/v1/incidents/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "inc-stage-a-001"
    assert data["status"] == "awaiting_approval"


@pytest.mark.asyncio
async def test_investigate_endpoint(client: AsyncClient):
    response = await client.post("/api/v1/incidents/investigate")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tool_trace"]) == 11
    assert data["hypotheses"][0]["confidence"] > 0.8


@pytest.mark.asyncio
async def test_download_mcap_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/incidents/inc-stage-a-001/recording.mcap")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert len(response.content) > 1000
