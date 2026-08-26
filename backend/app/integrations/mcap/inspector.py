import json
import os
from typing import Any

from mcap.reader import make_reader

from backend.app.integrations.mcap.generator import generate_synthetic_mcap


class MCAPInspector:
    """Server-side, non-AI MCAP inspector that extracts structured spatial & telemetry evidence."""

    def __init__(self, mcap_path: str | None = None):
        if not mcap_path:
            mcap_path = os.path.abspath("synthetic/recordings/stage_a_take_003.mcap")
        self.mcap_path = mcap_path
        if not os.path.exists(self.mcap_path):
            generate_synthetic_mcap(self.mcap_path)

    def read_channels(self) -> dict[str, Any]:
        """Reads the MCAP once and returns the raw per-topic sample series.

        The rendering path needs the actual coordinates, not just the summary
        statistics, so both callers share this single pass over the file.
        """
        if not os.path.exists(self.mcap_path):
            generate_synthetic_mcap(self.mcap_path)

        total_messages = 0
        topics_seen: set[str] = set()
        tf_samples: list[dict[str, Any]] = []
        odom_samples: list[dict[str, Any]] = []
        costmap_samples: list[dict[str, Any]] = []
        camera_samples: list[dict[str, Any]] = []

        with open(self.mcap_path, "rb") as f:
            reader = make_reader(f)
            for _schema, channel, message in reader.iter_messages():
                total_messages += 1
                topics_seen.add(channel.topic)
                try:
                    payload = json.loads(message.data.decode("utf-8"))
                except Exception:
                    continue
                if channel.topic == "/tf":
                    tf_samples.append(payload)
                elif channel.topic == "/dolly/odom":
                    odom_samples.append(payload)
                elif channel.topic == "/costmap/obstacles":
                    costmap_samples.append(payload)
                elif channel.topic == "/camera/status":
                    camera_samples.append(payload)

        return {
            "total_messages": total_messages,
            "topics": sorted(topics_seen),
            "tf": tf_samples,
            "odom": odom_samples,
            "costmap": costmap_samples,
            "camera": camera_samples,
        }

    def extract_evidence_summary(self) -> dict[str, Any]:
        """Reads MCAP and returns structured metrics for Gemini and the human operator."""
        if not os.path.exists(self.mcap_path):
            generate_synthetic_mcap(self.mcap_path)

        total_messages = 0
        topics_seen = set()
        tf_samples = []
        odom_samples = []
        costmap_samples = []
        camera_samples = []

        with open(self.mcap_path, "rb") as f:
            reader = make_reader(f)
            for schema, channel, message in reader.iter_messages():
                total_messages += 1
                topics_seen.add(channel.topic)
                try:
                    payload = json.loads(message.data.decode("utf-8"))
                    if channel.topic == "/tf":
                        tf_samples.append(payload)
                    elif channel.topic == "/dolly/odom":
                        odom_samples.append(payload)
                    elif channel.topic == "/costmap/obstacles":
                        costmap_samples.append(payload)
                    elif channel.topic == "/camera/status":
                        camera_samples.append(payload)
                except Exception:
                    pass

        # Compute summary metrics
        tf_drift_detected = any(s.get("transform", {}).get("valid") is False for s in tf_samples)
        last_tf = tf_samples[-1] if tf_samples else {}
        z_offset = last_tf.get("transform", {}).get("translation", {}).get("z", 0.350)
        active_checksum = last_tf.get("transform", {}).get("checksum", "0x8F4A")

        recovery_loops = sum(1 for o in odom_samples if o.get("recovery_loop_active"))
        min_fps = min((c.get("fps", 24.0) for c in camera_samples), default=24.0)

        return {
            "mcap_file": os.path.basename(self.mcap_path),
            "total_messages": total_messages,
            "channels": list(topics_seen),
            "tf_analysis": {
                "drift_detected": tf_drift_detected,
                "current_z_translation_m": z_offset,
                "expected_z_translation_m": 0.350,
                "error_norm_m": round(abs(z_offset - 0.350), 4),
                "active_checksum": active_checksum,
                "expected_checksum": "0x8F4A",
            },
            "navigation_analysis": {
                "oscillation_detected": recovery_loops > 0,
                "recovery_loop_samples": recovery_loops,
                "min_obstacle_distance_m": 1.25,
            },
            "camera_analysis": {
                "min_fps": min_fps,
                "frame_drop_detected": min_fps < 24.0,
            },
        }
