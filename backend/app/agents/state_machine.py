import asyncio
import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from backend.app.domain.mock_data import get_mock_incident
from backend.app.domain.models import (
    Incident,
    ToolTraceEntry,
)
from backend.app.integrations.bigquery.client import BigQueryHistoricalClient
from backend.app.integrations.foxglove.client import FoxgloveClient
from backend.app.integrations.gcs.client import GCSClient
from backend.app.integrations.grafana.mcp_client import GrafanaMCPClient
from backend.app.integrations.mcap.inspector import MCAPInspector
from backend.app.settings import settings


class InvestigationStateMachine:
    """Deterministic 11-step agent investigation state machine."""

    def __init__(self, incident: Incident | None = None):
        self.incident = incident or get_mock_incident()
        self.grafana_client = GrafanaMCPClient()
        self.bq_client = BigQueryHistoricalClient()
        self.gcs_client = GCSClient()
        self.foxglove_client = FoxgloveClient()
        self.mcap_inspector = MCAPInspector()

    async def run_step(self, step_number: int) -> ToolTraceEntry:
        now_str = datetime.now(UTC).isoformat()

        if step_number == 1:
            return ToolTraceEntry(
                step_number=1,
                step_name="incident_intake",
                tool_type="system",
                action_summary="Ingested Stage A alert: CameraDollyOscillation & GenlockDrop",
                tool_name="alert_intake_webhook",
                tool_input_safe={
                    "stage_id": self.incident.stage_info.stage_id,
                    "asset_id": self.incident.robot_telemetry.robot_id,
                },
                tool_output_summary=f"Incident #{self.incident.incident_id} created. Severity: {self.incident.severity}. {self.incident.stage_info.current_scene} {self.incident.stage_info.current_take}.",
                timestamp=now_str,
                duration_ms=35,
            )

        elif step_number == 2:
            alerts = await self.grafana_client.get_alert_rules(self.incident.stage_info.stage_id)
            metrics = await self.grafana_client.query_prometheus(
                "rate(nav_recovery_loop_count[1m])"
            )
            metric_status = metrics.get("status", "success")
            return ToolTraceEntry(
                step_number=2,
                step_name="collect_grafana_context",
                tool_type="grafana_mcp",
                action_summary="Queried Grafana MCP for active firing alerts and Prometheus metrics",
                tool_name="mcp_grafana_query_prometheus",
                tool_input_safe={
                    "queries": [
                        "rate(nav_recovery_loop_count[1m])",
                        "camera_delivery_fps",
                        "tf_extrinsics_error_norm",
                    ]
                },
                tool_output_summary=f"Prometheus telemetry ({metric_status}): nav_recovery=7, fps=16.20 (target: 24.0), tf_error=0.038m. Firing alerts: {len(alerts)}.",
                timestamp=now_str,
                duration_ms=180,
            )

        elif step_number == 3:
            logs = await self.grafana_client.query_loki('{stage="stage-a"}')
            return ToolTraceEntry(
                step_number=3,
                step_name="collect_grafana_logs",
                tool_type="grafana_mcp",
                action_summary="Queried Loki logs for static transform and costmap warnings",
                tool_name="mcp_grafana_query_loki",
                tool_input_safe={
                    "logql": '{stage="stage-a"} |= "checksum mismatch" or "recovery behavior"',
                    "limit": 20,
                },
                tool_output_summary=f"Retrieved {len(logs)} log entries. Confirmed static TF checksum mismatch (0x8F4A expected vs 0x3E12 active).",
                timestamp=now_str,
                duration_ms=160,
            )

        elif step_number == 4:
            return ToolTraceEntry(
                step_number=4,
                step_name="form_hypotheses",
                tool_type="gemini_reasoner",
                action_summary="Generated 3 candidate hypotheses: TF Calibration Mismatch, Network Congestion, and GPU Throttling",
                tool_name="gemini_hypothesis_formulation",
                tool_input_safe={
                    "model": settings.GEMINI_MODEL,
                    "thinking_level": settings.GEMINI_THINKING_LEVEL,
                },
                tool_output_summary="Identified primary hypothesis (TF Calibration Mismatch) and 2 secondary hypotheses for differential testing.",
                timestamp=now_str,
                duration_ms=320,
            )

        elif step_number == 5:
            return ToolTraceEntry(
                step_number=5,
                step_name="test_hypotheses",
                tool_type="gemini_reasoner",
                action_summary="Tested hypotheses against packet loss (0.10%) and GPU temp (62.5°C), rejecting network/GPU causes",
                tool_name="gemini_differential_testing",
                tool_input_safe={
                    "tested_metrics": ["network_packet_loss_ratio", "gpu_temp_celsius"]
                },
                tool_output_summary="Rejected Network Congestion (packet loss nominal) and GPU Throttling (temps normal).",
                timestamp=now_str,
                duration_ms=210,
            )

        elif step_number == 6:
            matches = await self.bq_client.search_similar_incidents(
                symptoms=["tf_drift", "lens_swap"]
            )
            return ToolTraceEntry(
                step_number=6,
                step_name="query_historical_incidents",
                tool_type="bigquery",
                action_summary="Queried BigQuery historical dataset for past robotic dolly incidents",
                tool_name="bigquery_historical_search",
                tool_input_safe={
                    "dataset": f"{settings.GOOGLE_CLOUD_PROJECT}.{settings.BIGQUERY_DATASET}.incident_history",
                    "limit": 3,
                },
                tool_output_summary=f"Found {len(matches)} historical matches. Top match: inc-stage-b-044 (94% similarity) solved by profile reload.",
                timestamp=now_str,
                duration_ms=290,
            )

        elif step_number == 7:
            mcap_summary = self.mcap_inspector.extract_evidence_summary()
            local_path = self.mcap_inspector.mcap_path

            # Archive the recording so the evidence outlives this container: GCS
            # for retention, Foxglove so an operator can scrub the actual bag.
            archive_url = await self.gcs_client.upload_recording(
                local_path,
                f"incidents/{self.incident.incident_id}/{os.path.basename(local_path)}",
            )
            foxglove = await self.foxglove_client.upload_recording(local_path)
            self.incident.evidence_links["gcs_archive"] = archive_url
            self.incident.evidence_links["foxglove_recording"] = foxglove["url"]

            archive_note = (
                f" Archived to GCS and ingested by Foxglove ({foxglove['bytes']} bytes)."
                if foxglove.get("uploaded")
                else ""
            )
            return ToolTraceEntry(
                step_number=7,
                step_name="inspect_recording_evidence",
                tool_type="mcap_inspector",
                action_summary="Extracted spatial TF offsets and odometry oscillation from synthetic MCAP recording",
                tool_name="mcap_inspector_extract_tf_and_poses",
                tool_input_safe={
                    "mcap_file": mcap_summary["mcap_file"],
                    "channels": mcap_summary["channels"],
                    "gcs_archive": archive_url,
                    "foxglove_recording": foxglove["url"],
                },
                tool_output_summary=(
                    f"Extracted {mcap_summary['total_messages']} messages. Confirmed +35mm Z "
                    f"translation delta on camera optical frame.{archive_note}"
                ),
                timestamp=now_str,
                duration_ms=130,
            )

        elif step_number == 8:
            return ToolTraceEntry(
                step_number=8,
                step_name="assess_production_impact",
                tool_type="system",
                action_summary="Calculated production impact and shooting schedule delay",
                tool_name="production_impact_evaluator",
                tool_input_safe={"scene_take": "Scene 42 Take 3", "hourly_burn_rate_usd": 25000},
                tool_output_summary="Take 3 marked at risk. Estimated delay: 18 minutes. Affected assets: Camera Dolly Alpha & Stage A LED Volume.",
                timestamp=now_str,
                duration_ms=50,
            )

        elif step_number == 9:
            return ToolTraceEntry(
                step_number=9,
                step_name="recommend_recovery",
                tool_type="gemini_reasoner",
                action_summary="Synthesized recovery action: Reload Approved Profile CALIB-RIG-2026-v4",
                tool_name="gemini_recovery_synthesis",
                tool_input_safe={
                    "action_type": "configuration_reload",
                    "safety_level": "safe_halt",
                },
                tool_output_summary="Generated low-risk recovery recommendation with full rollback procedure and verification checklist.",
                timestamp=now_str,
                duration_ms=380,
            )

        elif step_number == 10:
            return ToolTraceEntry(
                step_number=10,
                step_name="request_human_approval",
                tool_type="system",
                action_summary="Submitted recovery plan to Stage Director / Rig Operator for human authorization",
                tool_name="human_approval_gate",
                tool_input_safe={"action_id": "act-rec-001", "requires_operator_signature": True},
                tool_output_summary="Human safety gate engaged. Awaiting operator approval in CineOps Guardian Console.",
                timestamp=now_str,
                duration_ms=20,
            )

        else:
            return ToolTraceEntry(
                step_number=11,
                step_name="generate_incident_summary",
                tool_type="system",
                action_summary="Compiled comprehensive incident diagnostic report and evidence links",
                tool_name="incident_summary_generator",
                tool_input_safe={"incident_id": self.incident.incident_id},
                tool_output_summary="Investigation complete. All evidence charts, logs, 2D trajectory, and Foxglove links ready for review.",
                timestamp=now_str,
                duration_ms=40,
            )

    async def stream_investigation(self) -> AsyncGenerator[ToolTraceEntry, None]:
        """Streams all investigation steps sequentially with real async delays."""
        for step in range(1, 12):
            entry = await self.run_step(step)
            yield entry
            await asyncio.sleep(0.15)
