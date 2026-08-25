from fastapi import APIRouter

from backend.app.api.incidents import router as incidents_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(incidents_router)
