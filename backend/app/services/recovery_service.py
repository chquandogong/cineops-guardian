from datetime import UTC, datetime

from backend.app.domain.mock_data import get_recovered_telemetry
from backend.app.domain.models import Incident, ToolTraceEntry


class RecoveryService:
    """Handles simulated recovery actions, post-action telemetry re-verification, and safety gates."""

    async def execute_recovery(
        self, incident: Incident, action_id: str, operator_name: str = "Stage Director"
    ) -> Incident:
        now_str = datetime.now(UTC).isoformat()

        # 1. Update recommendation approval status
        for rec in incident.recommendations:
            if rec.action_id == action_id:
                rec.approval_status = "executed"
                rec.approved_by = operator_name
                rec.approval_timestamp = now_str

        # 2. Add verification trace entries
        incident.tool_trace.append(
            ToolTraceEntry(
                step_number=len(incident.tool_trace) + 1,
                step_name="verify_recovery_execution",
                tool_type="system",
                action_summary=f"Operator '{operator_name}' approved action {action_id}. Reloaded profile CALIB-RIG-2026-v4",
                tool_name="robot_calibration_reload_service",
                tool_input_safe={"profile": "CALIB-RIG-2026-v4", "approved_by": operator_name},
                tool_output_summary="Static transform matrices reloaded. Checksum updated to 0x8F4A (CRC VALID).",
                timestamp=now_str,
                duration_ms=250,
            )
        )

        incident.tool_trace.append(
            ToolTraceEntry(
                step_number=len(incident.tool_trace) + 1,
                step_name="post_recovery_telemetry_check",
                tool_type="grafana_mcp",
                action_summary="Re-queried Grafana MCP Prometheus telemetry after calibration reload",
                tool_name="mcp_grafana_verify_metrics",
                tool_input_safe={
                    "queries": [
                        "rate(nav_recovery_loop_count[1m])",
                        "camera_delivery_fps",
                        "tf_extrinsics_error_norm",
                    ]
                },
                tool_output_summary="Verification PASSED: nav_recovery=0, camera_fps=24.00, tf_error=0.000m, localization_confidence=0.96.",
                timestamp=now_str,
                duration_ms=190,
            )
        )

        # 3. Update Incident state to resolved with post-recovery telemetry
        incident.post_recovery_telemetry = get_recovered_telemetry()
        incident.robot_telemetry = get_recovered_telemetry()
        incident.status = "resolved"
        incident.stage_info.shooting_status = "active_take"
        incident.resolution_summary = (
            f"Successfully resolved at {now_str}. "
            f"Applied profile CALIB-RIG-2026-v4 authorized by {operator_name}. "
            f"All 4 verification criteria satisfied. Shooting resumed for Scene 42 Take 3."
        )

        return incident
