export interface StageHealth {
  stage_id: string;
  stage_name: string;
  current_scene: string;
  current_take: string;
  shooting_status: 'active_take' | 'paused' | 'calibrating' | 'standby';
  led_wall_sync: boolean;
  genlock_fps: number;
  timecode: string;
}

export interface RobotTelemetry {
  robot_id: string;
  robot_name: string;
  firmware_version: string;
  active_rig_profile: string;
  approved_rig_profile: string;
  tf_checksum_valid: boolean;
  battery_percentage: number;
  camera_fps: number;
  target_fps: number;
  dropped_frames_pct: number;
  encoder_latency_ms: number;
  gpu_utilization_pct: number;
  gpu_temp_celsius: number;
  network_rtt_ms: number;
  network_packet_loss_pct: number;
  localization_confidence: number;
  nav_recovery_loop_count: number;
  velocity_command_oscillation_hz: number;
  costmap_inflation_alert: boolean;
}

export interface TrajectoryPoint {
  timestamp_offset_s: number;
  planned_x: number;
  planned_y: number;
  actual_x: number;
  actual_y: number;
  velocity_mps: number;
  obstacle_distance_m: number;
  tf_error_norm_m: number;
  status: 'normal' | 'warning' | 'recovery_loop' | 'stopped';
}

export interface LokiLogEntry {
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'FATAL';
  service: string;
  message: string;
  metadata?: Record<string, string>;
}

export interface ToolTraceEntry {
  step_number: number;
  step_name: string;
  tool_type:
    | 'grafana_mcp'
    | 'bigquery'
    | 'mcap_inspector'
    | 'gemini_reasoner'
    | 'foxglove'
    | 'gcs'
    | 'system';
  action_summary: string;
  tool_name: string;
  tool_input_safe: Record<string, any>;
  tool_output_summary: string;
  timestamp: string;
  duration_ms: number;
  status: 'success' | 'warning' | 'error';
}

export interface Hypothesis {
  id: string;
  title: string;
  rank: number;
  confidence: number;
  status: 'supported' | 'rejected' | 'investigating';
  rationale: string;
  supporting_evidence: string[];
  conflicting_evidence: string[];
  missing_evidence: string[];
}

export interface ProductionImpact {
  current_take_at_risk: boolean;
  estimated_delay_minutes: number;
  affected_assets: string[];
  schedule_severity: 'low' | 'medium' | 'critical';
  financial_burn_rate_per_hour_usd: number;
}

export interface RecoveryRecommendation {
  action_id: string;
  title: string;
  action_description: string;
  risk_level: 'low' | 'medium' | 'high';
  requires_approval: boolean;
  approval_status: 'pending' | 'approved' | 'rejected' | 'executed';
  approved_by?: string | null;
  approval_timestamp?: string | null;
  expected_effect: string;
  rollback_instructions: string;
  success_criteria: string[];
}

export interface HistoricalIncidentMatch {
  incident_id: string;
  date: string;
  stage: string;
  asset_id: string;
  scene_take: string;
  symptoms: string;
  confirmed_root_cause: string;
  action_taken: string;
  delay_minutes: number;
  similarity_score: number;
}

export interface Incident {
  incident_id: string;
  title: string;
  severity: 'P1-CRITICAL' | 'P2-HIGH' | 'P3-MEDIUM' | 'P4-LOW';
  status: 'intake' | 'investigating' | 'recommendation_ready' | 'awaiting_approval' | 'recovering' | 'resolved';
  triggered_at: string;
  stage_info: StageHealth;
  robot_telemetry: RobotTelemetry;
  trajectory: TrajectoryPoint[];
  loki_logs: LokiLogEntry[];
  tool_trace: ToolTraceEntry[];
  hypotheses: Hypothesis[];
  production_impact: ProductionImpact;
  recommendations: RecoveryRecommendation[];
  historical_matches: HistoricalIncidentMatch[];
  evidence_links: Record<string, string>;
  post_recovery_telemetry?: RobotTelemetry | null;
  resolution_summary?: string | null;
}
