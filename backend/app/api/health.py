from fastapi import APIRouter

from backend.app.instance import instance_id
from backend.app.services.incident_service import incident_service
from backend.app.settings import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": settings.DEMO_MODE,
        "state_backend": incident_service.state_backend,
        "instance": instance_id(),
        "model": settings.GEMINI_MODEL,
    }


@router.get("/api/v1/status")
async def api_status():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "gcp_project": settings.GOOGLE_CLOUD_PROJECT,
        "location": settings.GOOGLE_CLOUD_LOCATION,
        "model": settings.GEMINI_MODEL,
        "thinking_level": settings.GEMINI_THINKING_LEVEL,
        "mode": settings.DEMO_MODE,
        "state_backend": incident_service.state_backend,
    }
