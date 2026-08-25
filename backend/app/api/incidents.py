import json
import os

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.app.domain.models import Incident
from backend.app.services.incident_service import incident_service

router = APIRouter(prefix="/incidents", tags=["Incidents"])


class ApprovalRequest(BaseModel):
    action_id: str
    operator_name: str = "Stage Director / Rig Operator"


@router.get("/current", response_model=Incident)
async def get_current_incident():
    return incident_service.get_current_incident()


@router.post("/investigate", response_model=Incident)
async def run_investigation():
    return await incident_service.run_investigation()


@router.get("/stream-trace")
async def stream_investigation_trace():
    async def event_generator():
        async for trace_entry in incident_service.stream_investigation_trace():
            yield {
                "event": "trace_step",
                "data": json.dumps(trace_entry.model_dump()),
            }
        yield {
            "event": "complete",
            "data": json.dumps({"status": "investigation_completed"}),
        }

    return EventSourceResponse(event_generator())


@router.post("/approve-recovery", response_model=Incident)
async def approve_recovery(req: ApprovalRequest):
    return await incident_service.approve_recovery(req.action_id, req.operator_name)


@router.post("/reset", response_model=Incident)
async def reset_incident():
    return incident_service.reset_incident()


@router.get("/{incident_id}/recording.mcap")
async def download_mcap_recording(incident_id: str):
    mcap_path = os.path.abspath("synthetic/recordings/stage_a_take_003.mcap")
    if not os.path.exists(mcap_path):
        from backend.app.integrations.mcap.generator import generate_synthetic_mcap

        generate_synthetic_mcap(mcap_path)
    return FileResponse(
        path=mcap_path,
        media_type="application/octet-stream",
        filename="stage_a_take_003_incident.mcap",
    )
