import logging
import os
from typing import Any

import httpx

from backend.app.settings import settings

logger = logging.getLogger(__name__)


class FoxgloveClient:
    """Client for the Foxglove Data Platform API.

    In `real` mode this registers the stage's robotic asset as a Foxglove device,
    uploads the incident's ROS2 `.mcap` recording, and returns the deep link an
    operator opens to scrub the recording in Foxglove. In `mock` mode (and on any
    API failure) it returns the app's local recording endpoint so the demo stays
    hermetic and deterministic.
    """

    API_BASE = "https://api.foxglove.dev/v1"

    def __init__(self) -> None:
        self.mode = settings.DEMO_MODE
        self.token = settings.FOXGLOVE_API_KEY
        self.org = settings.FOXGLOVE_ORG_SLUG
        self.device_name = settings.DEFAULT_ROBOT_ID
        self.local_fallback = "/api/v1/incidents/inc-stage-a-001/recording.mcap"

    def _enabled(self) -> bool:
        return bool(
            self.mode == "real" and self.token and not self.token.startswith("fox_sk_placeholder")
        )

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def _resolve_device_id(self, client: httpx.AsyncClient) -> str | None:
        """Finds the device for this stage asset, creating it on first sight."""
        resp = await client.get(f"{self.API_BASE}/devices", headers=self._headers)
        if resp.status_code == 200:
            for device in resp.json():
                if device.get("name") == self.device_name:
                    return device.get("id")

        created = await client.post(
            f"{self.API_BASE}/devices",
            headers=self._headers,
            json={"name": self.device_name},
        )
        if created.status_code in (200, 201):
            return created.json().get("id")

        logger.warning(
            f"Foxglove device resolve failed ({created.status_code}): {created.text[:200]}"
        )
        return None

    async def upload_recording(self, local_path: str) -> dict[str, Any]:
        """Uploads an MCAP recording to Foxglove and returns its identifiers.

        Returns a dict with `uploaded` (bool), `url` (operator deep link) and,
        when the upload succeeded, `device_id` / `filename`.
        """
        if not self._enabled() or not os.path.exists(local_path):
            return {"uploaded": False, "url": self.local_fallback}

        filename = os.path.basename(local_path)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                device_id = await self._resolve_device_id(client)
                if not device_id:
                    return {"uploaded": False, "url": self.local_fallback}

                link_resp = await client.post(
                    f"{self.API_BASE}/data/upload",
                    headers=self._headers,
                    json={"deviceId": device_id, "filename": filename},
                )
                if link_resp.status_code != 200:
                    logger.warning(
                        f"Foxglove upload link failed ({link_resp.status_code}): "
                        f"{link_resp.text[:200]}"
                    )
                    return {"uploaded": False, "url": self.local_fallback}

                signed_url = link_resp.json().get("link")
                if not signed_url:
                    return {"uploaded": False, "url": self.local_fallback}

                with open(local_path, "rb") as handle:
                    payload = handle.read()

                put_resp = await client.put(
                    signed_url,
                    content=payload,
                    headers={"Content-Type": "application/octet-stream"},
                )
                if put_resp.status_code not in (200, 201, 204):
                    logger.warning(f"Foxglove MCAP PUT failed ({put_resp.status_code})")
                    return {"uploaded": False, "url": self.local_fallback}

                logger.info(
                    f"Foxglove ingest accepted {filename} ({len(payload)} bytes) "
                    f"for device {device_id}"
                )
                return {
                    "uploaded": True,
                    "url": f"https://app.foxglove.dev/{self.org}/recordings",
                    "device_id": device_id,
                    "filename": filename,
                    "bytes": len(payload),
                }
        except Exception as e:
            logger.warning(f"Foxglove upload failed, using local recording endpoint: {e}")
            return {"uploaded": False, "url": self.local_fallback}

    async def list_recordings(self, limit: int = 5) -> list[dict[str, Any]]:
        """Lists recordings Foxglove has ingested for this organization."""
        if not self._enabled():
            return []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.API_BASE}/recordings",
                    headers=self._headers,
                    params={"limit": limit},
                )
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"Foxglove recordings list failed ({resp.status_code})")
        except Exception as e:
            logger.warning(f"Foxglove recordings list failed: {e}")
        return []
