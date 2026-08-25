from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class StageHealth(BaseModel):
    stage_id: str = "stage-a-virtual-prod"
    stage_name: str = "Stage A — Virtual Production Volume"
    current_scene: str = "Scene 42"
    current_take: str = "Take 3"
    shooting_status: Literal["active_take", "paused", "calibrating", "standby"] = "paused"
    led_wall_sync: bool = True
    genlock_fps: float = 24.00
    timecode: str = "14:22:08:19"


class RobotTelemetry(BaseModel):
    robot_id: str = "dolly-alpha-01"
    robot_name: str = "Camera Dolly Alpha"
    firmware_version: str = "v2.8.4-ros2-iron"
    active_rig_profile: str = "CALIB-RIG-2026-v3"
    approved_rig_profile: str = "CALIB-RIG-2026-v4"
    tf_checksum_valid: bool = False
    battery_percentage: float = 88.5
    camera_fps: float = 16.20
    target_fps: float = 24.00
    dropped_frames_pct: float = 32.5
    encoder_latency_ms: float = 48.2
    gpu_utilization_pct: float = 64.0
    gpu_temp_celsius: float = 62.5
    network_rtt_ms: float = 2.4
    network_packet_loss_pct: float = 0.10
    localization_confidence: float = 0.42
    nav_recovery_loop_count: int = 7
    velocity_command_oscillation_hz: float = 3.8
    costmap_inflation_alert: bool = True


class TrajectoryPoint(BaseModel):
    timestamp_offset_s: float
    planned_x: float
    planned_y: float
    actual_x: float
    actual_y: float
    velocity_mps: float
    obstacle_distance_m: float
    tf_error_norm_m: float
    status: Literal["normal", "warning", "recovery_loop", "stopped"]


class LokiLogEntry(BaseModel):
    timestamp: str
    level: Literal["INFO", "WARN", "ERROR", "FATAL"]
    service: str
    message: str
    metadata: dict[str, str] = Field(default_factory=dict)


class ToolTraceEntry(BaseModel):
    step_number: int
    step_name: str
    tool_type: Literal["grafana_mcp", "bigquery", "mcap_inspector", "gemini_reasoner", "system"]
    action_summary: str
    tool_name: str
    tool_input_safe: dict[str, Any]
    tool_output_summary: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    duration_ms: int = 120
    status: Literal["success", "warning", "error"] = "success"


class Hypothesis(BaseModel):
    id: str
    title: str
    rank: int
    confidence: float = Field(..., ge=0.0, le=1.0)
    status: Literal["supported", "rejected", "investigating"]
    rationale: str
    supporting_evidence: list[str] = Field(default_factory=list)
    conflicting_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)


class ProductionImpact(BaseModel):
    current_take_at_risk: bool = True
    estimated_delay_minutes: int = 18
    affected_assets: list[str] = Field(default_factory=list)
    schedule_severity: Literal["low", "medium", "critical"] = "critical"
    financial_burn_rate_per_hour_usd: int = 25000


class RecoveryRecommendation(BaseModel):
    action_id: str
    title: str
    action_description: str
    risk_level: Literal["low", "medium", "high"]
    requires_approval: bool = True
    approval_status: Literal["pending", "approved", "rejected", "executed"] = "pending"
    approved_by: str | None = None
    approval_timestamp: str | None = None
    expected_effect: str
    rollback_instructions: str
    success_criteria: list[str] = Field(default_factory=list)


class HistoricalIncidentMatch(BaseModel):
    incident_id: str
    date: str
    stage: str
    asset_id: str
    scene_take: str
    symptoms: str
    confirmed_root_cause: str
    action_taken: str
    delay_minutes: int
    similarity_score: float


class Incident(BaseModel):
    incident_id: str = "inc-stage-a-001"
    title: str = "Robotic Camera Dolly Avoidance Oscillation & Frame Jitter"
    severity: Literal["P1-CRITICAL", "P2-HIGH", "P3-MEDIUM", "P4-LOW"] = "P1-CRITICAL"
    status: Literal[
        "intake",
        "investigating",
        "recommendation_ready",
        "awaiting_approval",
        "recovering",
        "resolved",
    ] = "awaiting_approval"
    triggered_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    stage_info: StageHealth = Field(default_factory=StageHealth)
    robot_telemetry: RobotTelemetry = Field(default_factory=RobotTelemetry)
    trajectory: list[TrajectoryPoint] = Field(default_factory=list)
    loki_logs: list[LokiLogEntry] = Field(default_factory=list)
    tool_trace: list[ToolTraceEntry] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    production_impact: ProductionImpact = Field(default_factory=ProductionImpact)
    recommendations: list[RecoveryRecommendation] = Field(default_factory=list)
    historical_matches: list[HistoricalIncidentMatch] = Field(default_factory=list)
    evidence_links: dict[str, str] = Field(default_factory=dict)
    post_recovery_telemetry: RobotTelemetry | None = None
    resolution_summary: str | None = None
