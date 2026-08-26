import json
import os
import time

from mcap.writer import Writer


def generate_synthetic_mcap(
    output_path: str,
    *,
    drift_from: int = 10,
    drifted_z: float = 0.385,
) -> str:
    """Generates a Foxglove-compatible MCAP recording for the camera dolly.

    ``drift_from`` is the sample index at which the rig starts misbehaving; pass a
    value past the end of the recording to emit a clean take. ``drifted_z`` is the
    TF Z-translation the rig settles on, which the baseline needs to be able to
    vary — a baseline showing the *same* Z is what proves a comparison tool is
    doing real work rather than confirming a foregone conclusion.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "wb") as f:
        writer = Writer(f)
        writer.start()

        # Register JSON schema for robot telemetry
        schema_id = writer.register_schema(
            name="foxglove.JsonMessage",
            encoding="jsonschema",
            data=json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "number"},
                        "topic": {"type": "string"},
                        "data": {"type": "object"},
                    },
                }
            ).encode("utf-8"),
        )

        # Register channels
        ch_tf = writer.register_channel(
            schema_id=schema_id,
            topic="/tf",
            message_encoding="json",
        )
        ch_odom = writer.register_channel(
            schema_id=schema_id,
            topic="/dolly/odom",
            message_encoding="json",
        )
        ch_costmap = writer.register_channel(
            schema_id=schema_id,
            topic="/costmap/obstacles",
            message_encoding="json",
        )
        ch_camera = writer.register_channel(
            schema_id=schema_id,
            topic="/camera/status",
            message_encoding="json",
        )

        base_time_ns = int(time.time() * 1e9)

        # Write 30 seconds of simulated frames (30 messages per channel at 1Hz or 24Hz)
        for i in range(30):
            t_s = float(i)
            t_ns = base_time_ns + int(t_s * 1e9)

            # TF message
            is_drifted = i >= drift_from
            tf_data = {
                "header": {"seq": i, "stamp_ns": t_ns, "frame_id": "lidar_link"},
                "child_frame_id": "camera_optical_frame",
                "transform": {
                    "translation": {
                        "x": 0.120,
                        "y": 0.000,
                        "z": drifted_z if is_drifted else 0.350,
                    },
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                    "checksum": "0x3E12" if is_drifted else "0x8F4A",
                    "valid": not is_drifted,
                },
            }
            writer.add_message(
                channel_id=ch_tf,
                log_time=t_ns,
                data=json.dumps(tf_data).encode("utf-8"),
                publish_time=t_ns,
            )

            # Odometry message
            px = 1.0 + (min(i, 19) * 0.4)
            py = 2.0 + (0.28 * (1 if i % 2 == 0 else -1) if is_drifted else 0.0)
            odom_data = {
                "pose": {
                    "position": {"x": round(px, 3), "y": round(py, 3), "z": 0.0},
                    "orientation": {
                        "yaw_deg": 0.0 if not is_drifted else (5.0 if i % 2 == 0 else -5.0)
                    },
                },
                "twist": {
                    "linear": {"x": 0.40 if not is_drifted else 0.05, "y": 0.0, "z": 0.0},
                    "angular": {"z": 0.0 if not is_drifted else 0.15},
                },
                "recovery_loop_active": i >= drift_from + 4,
            }
            writer.add_message(
                channel_id=ch_odom,
                log_time=t_ns,
                data=json.dumps(odom_data).encode("utf-8"),
                publish_time=t_ns,
            )

            # Costmap obstacle message
            costmap_data = {
                "obstacle_count": 1 if is_drifted else 0,
                "closest_obstacle_m": round(
                    1.25 if i >= drift_from + 4 else max(2.5 - i * 0.1, 1.3), 2
                ),
                "phantom_inflation_detected": is_drifted,
                "inflation_radius_m": 0.45,
            }
            writer.add_message(
                channel_id=ch_costmap,
                log_time=t_ns,
                data=json.dumps(costmap_data).encode("utf-8"),
                publish_time=t_ns,
            )

            # Camera status message
            cam_data = {
                "fps": 16.2 if i >= drift_from + 2 else 24.0,
                "target_fps": 24.0,
                "genlock_locked": i < drift_from + 2,
                "dropped_frame_count": (i - drift_from - 2) * 8 if i >= drift_from + 2 else 0,
            }
            writer.add_message(
                channel_id=ch_camera,
                log_time=t_ns,
                data=json.dumps(cam_data).encode("utf-8"),
                publish_time=t_ns,
            )

        writer.finish()
    return output_path
