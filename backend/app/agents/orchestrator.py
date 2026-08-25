import logging

from backend.app.agents.prompts import (
    INVESTIGATION_SYSTEM_PROMPT,
    INVESTIGATION_USER_PROMPT_TEMPLATE,
)
from backend.app.agents.schemas import AgentInvestigationOutput
from backend.app.agents.state_machine import InvestigationStateMachine
from backend.app.domain.mock_data import get_mock_incident
from backend.app.domain.models import Incident
from backend.app.settings import settings

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Coordinates the AI reasoning and deterministic investigation workflow."""

    def __init__(self):
        self.mode = settings.DEMO_MODE
        self.model_name = settings.GEMINI_MODEL

    async def investigate_incident(self, incident_id: str = "inc-stage-a-001") -> Incident:
        incident = get_mock_incident()
        state_machine = InvestigationStateMachine(incident)

        traces = []
        async for trace_entry in state_machine.stream_investigation():
            traces.append(trace_entry)

        incident.tool_trace = traces
        incident.status = "awaiting_approval"

        if self.mode == "real":
            try:
                from google import genai
                from google.genai import types

                client = genai.Client()
                prompt = INVESTIGATION_USER_PROMPT_TEMPLATE.format(
                    incident_id=incident.incident_id,
                    stage_id=incident.stage_info.stage_id,
                    stage_name=incident.stage_info.stage_name,
                    scene_take=f"{incident.stage_info.current_scene} {incident.stage_info.current_take}",
                    active_alerts="CameraDollyOscillation, CameraGenlockFrameDrop",
                    camera_fps=incident.robot_telemetry.camera_fps,
                    dropped_frames_pct=incident.robot_telemetry.dropped_frames_pct,
                    localization_confidence=incident.robot_telemetry.localization_confidence,
                    nav_recovery_loop_count=incident.robot_telemetry.nav_recovery_loop_count,
                    tf_checksum_valid=incident.robot_telemetry.tf_checksum_valid,
                    active_profile=incident.robot_telemetry.active_rig_profile,
                    approved_profile=incident.robot_telemetry.approved_rig_profile,
                    network_packet_loss_pct=incident.robot_telemetry.network_packet_loss_pct,
                    network_rtt_ms=incident.robot_telemetry.network_rtt_ms,
                    gpu_temp_celsius=incident.robot_telemetry.gpu_temp_celsius,
                    gpu_utilization_pct=incident.robot_telemetry.gpu_utilization_pct,
                    loki_logs_text="\n".join(
                        [
                            f"[{log_item.level}] {log_item.service}: {log_item.message}"
                            for log_item in incident.loki_logs
                        ]
                    ),
                    historical_matches_text="\n".join(
                        [
                            f"- {h.incident_id}: {h.symptoms} -> {h.confirmed_root_cause}"
                            for h in incident.historical_matches
                        ]
                    ),
                    mcap_evidence_text="MCAP analysis: +35mm Z extrinsic translation delta, 16 recovery loop frames, 16.20 fps min frame rate.",
                )

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=INVESTIGATION_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=AgentInvestigationOutput,
                        thinking_config=types.ThinkingConfig(thinking_budget=1024),
                    ),
                )
                logger.info(f"Gemini reasoning completed successfully: {response.text[:100]}...")
            except Exception as e:
                logger.warning(f"Gemini API call failed or in fallback mode: {e}")

        return incident
