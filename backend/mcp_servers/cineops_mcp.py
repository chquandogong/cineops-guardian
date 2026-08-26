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

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx
from mcp.server.mcpserver import Image, MCPServer

from backend.app.integrations.bigquery.client import BigQueryHistoricalClient
from backend.app.integrations.gcs.client import GCSClient
from backend.app.integrations.mcap.generator import generate_synthetic_mcap
from backend.app.integrations.mcap.inspector import MCAPInspector
from backend.app.integrations.mcap.renderer import render_comparison, render_spatial_evidence
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


def _operator_link(recording_id: str | None = None, at_iso: str | None = None) -> str:
    """Deep link that opens the configured layout, at the flagged moment.

    A bare recordings URL drops the operator into the default layout with no
    topics enabled. Carrying the layout id and the timestamp is the difference
    between "here is a file" and "here is the moment it went wrong".
    """
    base = f"https://app.foxglove.dev/{settings.FOXGLOVE_ORG_SLUG}"
    if not recording_id:
        return f"{base}/recordings"
    url = f"{base}/view?ds=foxglove-stream&ds.recordingId={recording_id}"
    if settings.FOXGLOVE_LAYOUT_ID:
        url += f"&layoutId={settings.FOXGLOVE_LAYOUT_ID}"
    if at_iso:
        url += f"&time={quote(at_iso, safe='')}"
    return url


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


@server.tool(
    name="compare_with_baseline",
    description=(
        "Render the failing take beside a known-good take of the same rig on the "
        "same route, and return the frame plus the numeric deltas. A measurement "
        "only becomes an anomaly next to a baseline: use this to check whether the "
        "value you are about to blame actually differs from a take that finished "
        "clean. If a metric is identical in both takes it is normal for this rig "
        "and cannot be the root cause, however suspicious it looks on its own."
    ),
)
def compare_with_baseline() -> list:
    incident = MCAPInspector().read_channels()
    baseline_path = os.path.join(
        os.path.dirname(MCAPInspector().mcap_path), "baseline_nominal.mcap"
    )
    # A clean baseline never drifts; the ablation profile drifts identically to the
    # failing take, which must change the agent's conclusion.
    drifts = abs(settings.BASELINE_TF_Z - 0.350) > 1e-9
    generate_synthetic_mcap(
        baseline_path,
        drift_from=10 if drifts else 999,
        drifted_z=settings.BASELINE_TF_Z,
    )
    baseline = MCAPInspector(baseline_path).read_channels()

    def summarize(ch: dict[str, Any]) -> dict[str, Any]:
        tf = ch.get("tf") or []
        cam = ch.get("camera") or []
        return {
            "tf_z_translation_m": tf[-1]["transform"]["translation"]["z"] if tf else None,
            "tf_checksum": tf[-1]["transform"].get("checksum") if tf else None,
            "recovery_loop_samples": sum(
                1 for o in (ch.get("odom") or []) if o.get("recovery_loop_active")
            ),
            "min_fps": min((c.get("fps", 24.0) for c in cam), default=24.0),
        }

    inc_stats, base_stats = summarize(incident), summarize(baseline)
    identical = [k for k, v in base_stats.items() if inc_stats.get(k) == v]
    differing = {
        k: {"baseline": v, "failing": inc_stats.get(k)}
        for k, v in base_stats.items()
        if inc_stats.get(k) != v
    }
    payload: dict[str, Any] = {
        "baseline_take": "nominal reference run, same rig and route",
        "identical_metrics": identical,
        "differing_metrics": differing,
    }
    if differing:
        payload["note"] = (
            "Only the metrics under differing_metrics can explain the failure. "
            "Anything under identical_metrics is normal for this rig — do not cite "
            "it as a root cause."
        )
    else:
        # The interesting case. A model that has already formed a hypothesis will
        # happily ignore a passive note, so state the contradiction as a finding.
        payload["contradiction"] = (
            "NOTHING DIFFERS. Every metric you might blame — including the TF "
            "Z-translation and its checksum — is identical in a take that finished "
            "clean on this same rig. Whatever you were about to call the root cause "
            "is this rig's normal operating state and did NOT cause this failure. "
            "You must either identify a metric that actually differs, or report that "
            "the cause is not present in the telemetry you have and list what is "
            "missing. Do not restate the hypothesis you held before calling this tool."
        )
        payload["required_action"] = (
            "Set the primary hypothesis status to 'investigating', put the "
            "unexplained gap in missing_evidence, and do not claim a confident root "
            "cause from metrics this baseline shows to be normal."
        )
    return [
        json.dumps(payload, indent=1),
        Image(data=render_comparison(incident, baseline), format="png"),
    ]


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
        "operator_link_hint": (
            "Foxglove ingests asynchronously; call foxglove_list_recordings to get "
            "the recording id, then hand the operator its operator_link."
        ),
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
                "operator_link": _operator_link(r.get("id"), r.get("start")),
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
        "operator_link": _operator_link(at_iso=start_time),
        "note": (
            "Hand this link to the rig operator: it opens the incident-triage "
            "layout at the annotated moment rather than a bare file listing."
        ),
    }


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
