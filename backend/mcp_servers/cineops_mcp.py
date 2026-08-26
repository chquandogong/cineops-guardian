#!/usr/bin/env python3
"""CineOps Guardian MCP server.

Exposes the stage-side capabilities that have no official MCP server of their own
— Foxglove Data Platform, BigQuery incident history, GCS evidence archive and the
local ROS2 MCAP inspector — as Model Context Protocol tools over stdio.

Grafana is deliberately absent here: it is served by the official
`grafana/mcp-grafana` server, which the agent connects to as a second MCP server.

Run standalone for debugging:
    python -m backend.mcp_servers.cineops_mcp
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import httpx
from mcp.server.mcpserver import Image, MCPServer

from backend.app.integrations.bigquery.client import BigQueryHistoricalClient
from backend.app.integrations.gcs.client import GCSClient
from backend.app.integrations.mcap.inspector import MCAPInspector
from backend.app.integrations.mcap.renderer import render_spatial_evidence
from backend.app.settings import settings

logger = logging.getLogger(__name__)

FOXGLOVE_API = "https://api.foxglove.dev/v1"

server = MCPServer(
    name="cineops-guardian",
    version="1.0.0",
    instructions=(
        "Stage-side tools for diagnosing virtual production incidents: inspect ROS2 "
        "MCAP recordings, search historical incidents in BigQuery, archive evidence to "
        "Google Cloud Storage, and publish recordings and annotations to Foxglove."
    ),
)


def _foxglove_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.FOXGLOVE_API_KEY}",
        "Content-Type": "application/json",
    }


def _foxglove_ready() -> bool:
    key = settings.FOXGLOVE_API_KEY
    return bool(key) and not key.startswith("fox_sk_placeholder")


# --------------------------------------------------------------------------- #
# ROS2 / MCAP
# --------------------------------------------------------------------------- #
@server.tool(
    name="inspect_mcap_recording",
    description=(
        "Parse the incident's multi-channel ROS2 .mcap recording and return measured "
        "spatial evidence: per-topic message counts, the static transform (TF) "
        "translation delta between the camera optical frame and the LiDAR link in "
        "metres, odometry oscillation, costmap obstacle proximity and camera frame "
        "rate. Use this to confirm or refute a physical calibration hypothesis with "
        "real numbers instead of assuming them."
    ),
)
def inspect_mcap_recording() -> dict[str, Any]:
    inspector = MCAPInspector()
    summary = inspector.extract_evidence_summary()
    summary["local_path"] = inspector.mcap_path
    return summary


@server.tool(
    name="render_spatial_evidence",
    description=(
        "Render the ROS2 MCAP telemetry as an annotated image and return it, so you "
        "can look at the incident instead of only reading numbers. The frame shows a "
        "top-down view of the dolly's path against the costmap inflation that is "
        "blocking it, plus the TF Z-translation against its approved value and the "
        "camera frame rate against target. Use it to judge the *shape* of the "
        "failure — a smooth traverse that turns into a tight zig-zag at a specific "
        "point is what an oscillating avoidance loop looks like, and is hard to see "
        "in summary statistics. Describe what you actually observe in the image."
    ),
)
def render_spatial_evidence_tool() -> Image:
    channels = MCAPInspector().read_channels()
    return Image(data=render_spatial_evidence(channels), format="png")


# --------------------------------------------------------------------------- #
# BigQuery
# --------------------------------------------------------------------------- #
@server.tool(
    name="search_incident_history",
    description=(
        "Search the BigQuery incident-history dataset for past stage incidents on the "
        "same class of asset, ordered by similarity. Returns the confirmed root cause "
        "and the recovery action that resolved each one, so a proven procedure can be "
        "reused instead of invented."
    ),
)
async def search_incident_history(
    asset_type: str = "camera_dolly", limit: int = 3
) -> dict[str, Any]:
    client = BigQueryHistoricalClient()
    matches = await client.search_similar_incidents(symptoms=[], asset_type=asset_type, limit=limit)
    return {
        "dataset": f"{settings.GOOGLE_CLOUD_PROJECT}.{settings.BIGQUERY_DATASET}.incident_history",
        "asset_type": asset_type,
        "match_count": len(matches),
        "matches": [m.model_dump() for m in matches],
    }


# --------------------------------------------------------------------------- #
# Google Cloud Storage
# --------------------------------------------------------------------------- #
@server.tool(
    name="archive_evidence_to_gcs",
    description=(
        "Archive the incident's MCAP recording to the Google Cloud Storage evidence "
        "bucket so the raw telemetry outlives the container that diagnosed it. "
        "Returns the archive URL. Safe and idempotent: it writes evidence only and "
        "never touches stage hardware."
    ),
)
async def archive_evidence_to_gcs(incident_id: str = "inc-stage-a-001") -> dict[str, Any]:
    inspector = MCAPInspector()
    local_path = inspector.mcap_path
    blob = f"incidents/{incident_id}/{os.path.basename(local_path)}"
    url = await GCSClient().upload_recording(local_path, blob)
    return {"bucket": settings.GCS_BUCKET, "object": blob, "url": url}


# --------------------------------------------------------------------------- #
# Foxglove Data Platform
# --------------------------------------------------------------------------- #
def _shift_iso(start: str, seconds: int) -> str:
    """Returns `start` advanced by `seconds`, or `start` unchanged if unparseable."""
    try:
        begin = datetime.fromisoformat(start.replace("Z", "+00:00"))
    except ValueError:
        return start
    return (begin + timedelta(seconds=max(seconds, 0))).isoformat().replace("+00:00", "Z")


async def _resolve_device(client: httpx.AsyncClient, device_name: str) -> str | None:
    resp = await client.get(f"{FOXGLOVE_API}/devices", headers=_foxglove_headers())
    if resp.status_code == 200:
        for device in resp.json():
            if device.get("name") == device_name:
                return device.get("id")
    created = await client.post(
        f"{FOXGLOVE_API}/devices", headers=_foxglove_headers(), json={"name": device_name}
    )
    if created.status_code in (200, 201):
        return created.json().get("id")
    logger.warning("Foxglove device resolve failed: %s %s", created.status_code, created.text[:200])
    return None


@server.tool(
    name="foxglove_upload_recording",
    description=(
        "Upload the incident's ROS2 .mcap recording to the Foxglove Data Platform, "
        "registering the stage asset as a Foxglove device if it is not known yet. "
        "Foxglove ingests the bag so a human rig operator can scrub the actual "
        "telemetry. Returns the device id and the operator-facing recordings URL. "
        "Uploads data only; it cannot command the robot."
    ),
)
async def foxglove_upload_recording(
    device_name: str = "", incident_id: str = "inc-stage-a-001"
) -> dict[str, Any]:
    device_name = device_name or settings.DEFAULT_ROBOT_ID
    if not _foxglove_ready():
        return {"uploaded": False, "reason": "Foxglove API key not configured"}

    inspector = MCAPInspector()
    local_path = inspector.mcap_path
    if not os.path.exists(local_path):
        return {"uploaded": False, "reason": f"recording not found at {local_path}"}

    filename = os.path.basename(local_path)
    async with httpx.AsyncClient(timeout=60.0) as client:
        device_id = await _resolve_device(client, device_name)
        if not device_id:
            return {"uploaded": False, "reason": "could not resolve Foxglove device"}

        link_resp = await client.post(
            f"{FOXGLOVE_API}/data/upload",
            headers=_foxglove_headers(),
            json={"deviceId": device_id, "filename": filename},
        )
        if link_resp.status_code != 200:
            return {
                "uploaded": False,
                "reason": f"upload link failed ({link_resp.status_code})",
            }

        signed_url = link_resp.json().get("link")
        with open(local_path, "rb") as handle:
            payload = handle.read()
        put_resp = await client.put(
            signed_url, content=payload, headers={"Content-Type": "application/octet-stream"}
        )
        if put_resp.status_code not in (200, 201, 204):
            return {"uploaded": False, "reason": f"PUT failed ({put_resp.status_code})"}

    return {
        "uploaded": True,
        "device_id": device_id,
        "device_name": device_name,
        "filename": filename,
        "bytes": len(payload),
        "incident_id": incident_id,
        "recordings_url": f"https://app.foxglove.dev/{settings.FOXGLOVE_ORG_SLUG}/recordings",
    }


@server.tool(
    name="foxglove_list_recordings",
    description=(
        "List recordings the Foxglove Data Platform has ingested for this "
        "organization, newest first, with their device, size and time span. Use it to "
        "confirm an upload was ingested or to find an earlier take to compare against."
    ),
)
async def foxglove_list_recordings(limit: int = 5) -> dict[str, Any]:
    if not _foxglove_ready():
        return {"recordings": [], "reason": "Foxglove API key not configured"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{FOXGLOVE_API}/recordings", headers=_foxglove_headers(), params={"limit": limit}
        )
        if resp.status_code != 200:
            return {"recordings": [], "reason": f"list failed ({resp.status_code})"}
        rows = resp.json()
    return {
        "count": len(rows),
        "recordings": [
            {
                "id": r.get("id"),
                "filename": r.get("path") or r.get("filename"),
                "bytes": r.get("size"),
                "device": (r.get("device") or {}).get("name"),
                "start": r.get("start"),
            }
            for r in rows
        ],
    }


@server.tool(
    name="foxglove_create_event",
    description=(
        "Annotate a time span on the Foxglove timeline with an incident event so the "
        "finding is pinned to the recording for whoever opens it next. Supply the "
        "device name, an ISO-8601 start time, a duration, and metadata describing the "
        "root cause. Writes an annotation only; it cannot command the robot."
    ),
)
async def foxglove_create_event(
    start_time: str,
    duration_seconds: int = 30,
    device_name: str = "",
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    device_name = device_name or settings.DEFAULT_ROBOT_ID
    if not _foxglove_ready():
        return {"created": False, "reason": "Foxglove API key not configured"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        device_id = await _resolve_device(client, device_name)
        if not device_id:
            return {"created": False, "reason": "could not resolve Foxglove device"}
        body = {
            "deviceId": device_id,
            "start": start_time,
            "end": _shift_iso(start_time, duration_seconds),
            "metadata": {k: str(v) for k, v in (metadata or {}).items()},
        }
        resp = await client.post(f"{FOXGLOVE_API}/events", headers=_foxglove_headers(), json=body)
        if resp.status_code not in (200, 201):
            return {
                "created": False,
                "reason": f"event create failed ({resp.status_code}): {resp.text[:160]}",
            }
        created = resp.json()
    return {
        "created": True,
        "event_id": created.get("id"),
        "device_id": device_id,
        "duration_seconds": duration_seconds,
    }


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
