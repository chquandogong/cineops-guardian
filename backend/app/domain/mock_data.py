from datetime import UTC, datetime

from backend.app.domain.models import (
    HistoricalIncidentMatch,
    Hypothesis,
    Incident,
    LokiLogEntry,
    ProductionImpact,
    RecoveryRecommendation,
    RobotTelemetry,
    StageHealth,
    ToolTraceEntry,
    TrajectoryPoint,
)


def generate_mock_trajectory() -> list[TrajectoryPoint]:
    """Generates 30 seconds of synchronized planned vs actual trajectory demonstrating oscillation."""
    points = []
    # 0 to 10s: Normal tracking
    for i in range(10):
        t = float(i)
        px = 1.0 + t * 0.4
        py = 2.0
        points.append(
            TrajectoryPoint(
                timestamp_offset_s=t,
                planned_x=round(px, 3),
                planned_y=round(py, 3),
                actual_x=round(px + 0.01, 3),
                actual_y=round(py + 0.01, 3),
                velocity_mps=0.40,
                obstacle_distance_m=round(3.5 - t * 0.15, 2),
                tf_error_norm_m=0.002,
                status="normal",
            )
        )

    # 10 to 20s: TF drift begins near obstacle, costmap phantom inflation, velocity oscillation
    for i in range(10, 20):
        t = float(i)
        px = 1.0 + t * 0.4
        py = 2.0
        # Sinusoidal oscillation in actual Y due to avoidance jitter
        oscillation = 0.28 * (1 if i % 2 == 0 else -1)
        tf_err = min(0.038, 0.005 + (i - 10) * 0.0035)
        points.append(
            TrajectoryPoint(
                timestamp_offset_s=t,
                planned_x=round(px, 3),
                planned_y=round(py, 3),
                actual_x=round(px - 0.15, 3),
                actual_y=round(py + oscillation, 3),
                velocity_mps=round(0.40 - (i - 10) * 0.035, 2),
                obstacle_distance_m=round(1.8 - (i - 10) * 0.05, 2),
                tf_error_norm_m=round(tf_err, 4),
                status="warning" if i < 14 else "recovery_loop",
            )
        )

    # 20 to 28s: Full navigation recovery loop, dolly jerks back and forth
    for i in range(20, 28):
        t = float(i)
        px = 1.0 + 19 * 0.4  # Stopped advance
        py = 2.0
        oscillation = 0.35 * (1 if i % 2 == 0 else -1)
        points.append(
            TrajectoryPoint(
                timestamp_offset_s=t,
                planned_x=round(px, 3),
                planned_y=round(py, 3),
                actual_x=round(px - 0.20 + (i % 3) * 0.05, 3),
                actual_y=round(py + oscillation, 3),
                velocity_mps=0.05,
                obstacle_distance_m=1.25,
                tf_error_norm_m=0.038,
                status="recovery_loop",
            )
        )
    return points


def get_mock_incident() -> Incident:
    now_str = datetime.now(UTC).isoformat()

    logs = [
        LokiLogEntry(
            timestamp="14:21:45.102Z",
            level="INFO",
            service="dolly-rig-mgr",
            message="Lens swap acknowledged: CinePrime 35mm T1.5 mounted on Camera Dolly Alpha.",
            metadata={"rig_profile": "CALIB-RIG-2026-v3", "operator": "cam_tech_02"},
        ),
        LokiLogEntry(
            timestamp="14:21:48.330Z",
            level="WARN",
            service="tf2_ros_broadcaster",
            message="Static transform checksum mismatch for [camera_optical_frame] -> [lidar_link]. Expected CRC 0x8F4A, active 0x3E12.",
            metadata={"frame_id": "camera_optical_frame", "parent_id": "lidar_link"},
        ),
        LokiLogEntry(
            timestamp="14:22:01.050Z",
            level="WARN",
            service="costmap_2d",
            message="Rapid obstacle inflation detected near coordinates (x: 4.82, y: 2.15). Clearance threshold violated (1.25m < 1.50m).",
            metadata={"obstacle_id": "lighting_c_stand_03"},
        ),
        LokiLogEntry(
            timestamp="14:22:03.410Z",
            level="ERROR",
            service="nav2_controller",
            message="Navigation recovery behavior entered: [SpinRecovery -> BackupRecovery]. Consecutive retry count: 7.",
            metadata={"planner": "DWBLocalPlanner", "recovery_count": "7"},
        ),
        LokiLogEntry(
            timestamp="14:22:04.990Z",
            level="ERROR",
            service="camera_streamer",
            message="Frame delivery degradation: 32.5% frames dropped in last 5000ms. Optical genlock jitter exceeded 18ms.",
            metadata={"actual_fps": "16.20", "target_fps": "24.00"},
        ),
    ]

    tool_traces = [
        ToolTraceEntry(
            step_number=1,
            step_name="incident_intake",
            tool_type="system",
            action_summary="Ingested Stage A alert: CameraDollyOscillation & GenlockDrop",
            tool_name="alert_intake_webhook",
            tool_input_safe={"stage_id": "stage-a-virtual-prod", "asset_id": "dolly-alpha-01"},
            tool_output_summary="Incident #inc-stage-a-001 created. Severity: P1-CRITICAL. Scene 42 Take 3.",
            duration_ms=45,
            status="success",
        ),
        ToolTraceEntry(
            step_number=2,
            step_name="collect_grafana_context",
            tool_type="grafana_mcp",
            action_summary="Queried Grafana MCP for active alerts and Prometheus timeseries",
            tool_name="mcp_grafana_query_prometheus",
            tool_input_safe={
                "queries": [
                    "rate(nav_recovery_loop_count[1m])",
                    "camera_delivery_fps",
                    "tf_extrinsics_error_norm",
                    "network_packet_loss_ratio",
                ],
                "time_range": "now-5m to now",
            },
            tool_output_summary="Prometheus telemetry: nav_recovery=7, fps dropped from 24.0 to 16.2, tf_error=0.038m, packet_loss=0.10%.",
            duration_ms=210,
            status="success",
        ),
        ToolTraceEntry(
            step_number=3,
            step_name="collect_grafana_logs",
            tool_type="grafana_mcp",
            action_summary="Queried Loki logs for service='tf2_ros_broadcaster' and service='costmap_2d'",
            tool_name="mcp_grafana_query_loki",
            tool_input_safe={
                "logql": '{stage="stage-a"} |= "checksum mismatch" or "recovery behavior"',
                "limit": 20,
            },
            tool_output_summary="Found 5 critical logs confirming TF checksum mismatch (0x8F4A vs 0x3E12) and costmap obstacle oscillation.",
            duration_ms=180,
            status="success",
        ),
        ToolTraceEntry(
            step_number=4,
            step_name="query_historical_incidents",
            tool_type="bigquery",
            action_summary="Searched BigQuery historical incidents for TF mismatch and nav oscillation on Stage A/B",
            tool_name="bigquery_historical_search",
            tool_input_safe={
                "dataset": "cineops_guardian.incident_history",
                "filter_symptoms": ["tf_drift", "lens_swap", "recovery_loop"],
                "limit": 3,
            },
            tool_output_summary="Matched 2 prior incidents. Most similar: inc-stage-b-044 (94% match) resolved in 4m by reloading approved rig profile.",
            duration_ms=310,
            status="success",
        ),
        ToolTraceEntry(
            step_number=5,
            step_name="inspect_recording_evidence",
            tool_type="mcap_inspector",
            action_summary="Parsed synthetic MCAP telemetry recording /recordings/stage_a_take_003.mcap",
            tool_name="mcap_inspector_extract_tf_and_poses",
            tool_input_safe={
                "mcap_uri": "gs://cineops-guardian-evidence/stage_a_take_003.mcap",
                "topics": ["/tf", "/dolly/odom", "/costmap/obstacles", "/camera/status"],
            },
            tool_output_summary="Extracted 320 messages. Verified spatial offset (+35mm Z) between optical center and LiDAR ground plane projection.",
            duration_ms=140,
            status="success",
        ),
        ToolTraceEntry(
            step_number=6,
            step_name="gemini_reasoning_and_ranking",
            tool_type="gemini_reasoner",
            action_summary="Gemini 3.7 Flash evaluated hypotheses, ruled out network/GPU overload, and synthesized recovery plan",
            tool_name="gemini_structured_investigation",
            tool_input_safe={"model": "gemini-3.7-flash", "thinking_level": "HIGH"},
            tool_output_summary="Formulated 3 ranked hypotheses. Primary: Stale LiDAR/Camera TF Extrinsics (88% confidence). Safe recovery plan formulated.",
            duration_ms=450,
            status="success",
        ),
    ]

    hypotheses = [
        Hypothesis(
            id="hyp-01",
            title="Stale LiDAR / Camera TF Extrinsic Calibration After Rig Swap",
            rank=1,
            confidence=0.88,
            status="supported",
            rationale="Hardware rig change at 14:21:45 mounted 35mm Prime lens (+35mm bracket delta) without updating static transform snapshot. LiDAR point cloud projection misaligns with optical tracking, causing phantom obstacle inflation in costmap.",
            supporting_evidence=[
                "Loki log confirms static transform hash mismatch (0x8F4A expected vs 0x3E12 active).",
                "MCAP inspection reveals 0.038m extrinsic translation vector offset on Z-axis.",
                "BigQuery historical incident inc-stage-b-044 showed identical symptoms after lens change.",
                "Velocity command oscillation coincides precisely with obstacle proximity.",
            ],
            conflicting_evidence=[],
            missing_evidence=[],
        ),
        Hypothesis(
            id="hyp-02",
            title="Stage Wi-Fi / Private 5G Network Congestion & Packet Jitter",
            rank=2,
            confidence=0.12,
            status="rejected",
            rationale="Checked network RTT and packet loss telemetry. Network remains completely stable, ruling out network dropouts as the cause.",
            supporting_evidence=[],
            conflicting_evidence=[
                "Prometheus network_packet_loss_ratio is at baseline 0.10% (well below 2.0% threshold).",
                "Network RTT steady at 2.4ms with 0.3ms jitter.",
            ],
            missing_evidence=[],
        ),
        Hypothesis(
            id="hyp-03",
            title="Onboard Jetson GPU / Video Encoder Thermal Throttling",
            rank=3,
            confidence=0.08,
            status="rejected",
            rationale="Investigated GPU temperature and encoder queue depth. System thermals and GPU load are within nominal operating limits.",
            supporting_evidence=[],
            conflicting_evidence=[
                "GPU core temperature steady at 62.5°C (thermal throttle point is 85.0°C).",
                "GPU utilization at 64.0% with adequate VRAM headroom.",
            ],
            missing_evidence=[],
        ),
    ]

    recommendations = [
        RecoveryRecommendation(
            action_id="act-rec-001",
            title="Reload Approved Rig Calibration Profile & Verify TF Checksum",
            action_description="Instruct robotic dolly controller to halt motion, reload approved calibration profile 'CALIB-RIG-2026-v4' from stage config repository, and recompute static transform matrices.",
            risk_level="low",
            requires_approval=True,
            approval_status="pending",
            expected_effect="Eliminates phantom obstacle inflation in costmap, clears navigation recovery loop, and restores 24.00 fps genlocked frame delivery.",
            rollback_instructions="If TF calibration fails to converge, revert controller to safe manual e-stop mode and roll back to baseline snapshot 'CALIB-RIG-2026-v3'.",
            success_criteria=[
                "Static TF checksum matches approved profile CRC 0x8F4A.",
                "Localization confidence increases above 0.85.",
                "Navigation recovery loop count drops to 0.",
                "Camera frame rate stabilizes at 24.00 fps.",
            ],
        )
    ]

    historical_matches = [
        HistoricalIncidentMatch(
            incident_id="inc-stage-b-044",
            date="2026-08-10",
            stage="Stage B — Virtual Volume",
            asset_id="dolly-bravo-02",
            scene_take="Scene 18 Take 2",
            symptoms="Lens swap to 50mm Anamorphic caused dolly avoidance jitter and dropped camera sync.",
            confirmed_root_cause="Stale URDF TF matrix between optical nodal point and base LiDAR.",
            action_taken="Reloaded approved calibration profile CALIB-RIG-STAGE-B-v2.",
            delay_minutes=4,
            similarity_score=0.94,
        ),
        HistoricalIncidentMatch(
            incident_id="inc-stage-a-019",
            date="2026-07-28",
            stage="Stage A — Virtual Volume",
            asset_id="dolly-alpha-01",
            scene_take="Scene 09 Take 5",
            symptoms="Dolly paused during rapid dolly-in near lighting scaffold with costmap warning.",
            confirmed_root_cause="LiDAR mount vibration loosening + 20mm extrinsic calibration shift.",
            action_taken="Tightened mount bracket and executed recalibration script.",
            delay_minutes=7,
            similarity_score=0.82,
        ),
    ]

    return Incident(
        incident_id="inc-stage-a-001",
        title="Robotic Camera Dolly Avoidance Oscillation & Frame Jitter",
        severity="P1-CRITICAL",
        status="awaiting_approval",
        triggered_at=now_str,
        stage_info=StageHealth(),
        robot_telemetry=RobotTelemetry(),
        trajectory=generate_mock_trajectory(),
        loki_logs=logs,
        tool_trace=tool_traces,
        hypotheses=hypotheses,
        production_impact=ProductionImpact(
            current_take_at_risk=True,
            estimated_delay_minutes=18,
            affected_assets=[
                "Camera Dolly Alpha",
                "ARRI Alexa Mini LF",
                "OptiTrack Rig A",
                "Stage A LED Volume",
            ],
            schedule_severity="critical",
            financial_burn_rate_per_hour_usd=25000,
        ),
        recommendations=recommendations,
        historical_matches=historical_matches,
        evidence_links={
            "grafana_dashboard": "https://cineops.grafana.net/d/stage-a-dolly/camera-dolly-stage-a?orgId=1",
            "foxglove_recording": "/api/v1/incidents/inc-stage-a-001/recording.mcap",
            "bigquery_table": "https://console.cloud.google.com/bigquery?project=project-55fbcfd2-0ad6-4c99-a25&p=cineops_guardian&d=incident_history",
        },
    )


def get_recovered_telemetry() -> RobotTelemetry:
    """Returns normalized telemetry after approved recovery profile is executed."""
    return RobotTelemetry(
        robot_id="dolly-alpha-01",
        robot_name="Camera Dolly Alpha",
        firmware_version="v2.8.4-ros2-iron",
        active_rig_profile="CALIB-RIG-2026-v4",
        approved_rig_profile="CALIB-RIG-2026-v4",
        tf_checksum_valid=True,
        battery_percentage=87.8,
        camera_fps=24.00,
        target_fps=24.00,
        dropped_frames_pct=0.0,
        encoder_latency_ms=16.4,
        gpu_utilization_pct=52.0,
        gpu_temp_celsius=58.2,
        network_rtt_ms=2.2,
        network_packet_loss_pct=0.05,
        localization_confidence=0.96,
        nav_recovery_loop_count=0,
        velocity_command_oscillation_hz=0.0,
        costmap_inflation_alert=False,
    )
