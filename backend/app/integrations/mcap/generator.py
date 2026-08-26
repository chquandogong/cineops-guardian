import json
import math
import os
import time

from mcap.writer import Writer

from backend.app.integrations.mcap.foxglove_schemas import (
    SCHEMAS,
    point_cloud,
    quat_from_yaw,
    stamp,
)


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

        # Visualization topics carrying the well-known Foxglove schemas. The
        # analytic topics above stay as they are for the inspector; these are what
        # make the recording actually render in a 3D panel, the way a real robot
        # bag does.
        fg_ids = {
            name: writer.register_schema(
                name=name, encoding="jsonschema", data=json.dumps(schema).encode("utf-8")
            )
            for name, schema in SCHEMAS.items()
        }
        ch_viz_tf = writer.register_channel(
            schema_id=fg_ids["foxglove.FrameTransform"],
            topic="/viz/tf",
            message_encoding="json",
        )
        ch_viz_pose = writer.register_channel(
            schema_id=fg_ids["foxglove.PoseInFrame"],
            topic="/viz/dolly_pose",
            message_encoding="json",
        )
        ch_viz_cloud = writer.register_channel(
            schema_id=fg_ids["foxglove.PointCloud"],
            topic="/viz/lidar_points",
            message_encoding="json",
        )
        ch_viz_scene = writer.register_channel(
            schema_id=fg_ids["foxglove.SceneUpdate"],
            topic="/viz/costmap",
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

            # ---- visualization: TF tree, dolly pose, LiDAR, costmap geometry
            yaw = math.radians(odom_data["pose"]["orientation"]["yaw_deg"])
            for parent, child, tr, rot in (
                ("world", "base_link", {"x": px, "y": py, "z": 0.0}, quat_from_yaw(yaw)),
                (
                    "base_link",
                    "lidar_link",
                    {"x": 0.0, "y": 0.0, "z": 0.60},
                    {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                ),
                (
                    "lidar_link",
                    "camera_optical_frame",
                    {"x": 0.120, "y": 0.0, "z": tf_data["transform"]["translation"]["z"]},
                    {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                ),
            ):
                writer.add_message(
                    channel_id=ch_viz_tf,
                    log_time=t_ns,
                    data=json.dumps(
                        {
                            "timestamp": stamp(t_ns),
                            "parent_frame_id": parent,
                            "child_frame_id": child,
                            "translation": tr,
                            "rotation": rot,
                        }
                    ).encode("utf-8"),
                    publish_time=t_ns,
                )

            writer.add_message(
                channel_id=ch_viz_pose,
                log_time=t_ns,
                data=json.dumps(
                    {
                        "timestamp": stamp(t_ns),
                        "frame_id": "world",
                        "pose": {
                            "position": {"x": px, "y": py, "z": 0.0},
                            "orientation": quat_from_yaw(yaw),
                        },
                    }
                ).encode("utf-8"),
                publish_time=t_ns,
            )

            # A LiDAR sweep of the set floor and the lighting scaffold. Once the
            # calibration is stale the returns are projected with the wrong Z, which
            # is what the costmap then inflates into a phantom obstacle.
            z_error = tf_data["transform"]["translation"]["z"] - 0.350
            sweep = []
            for k in range(72):
                a = (k / 72) * 2 * math.pi
                r = 3.4 + 0.35 * math.sin(a * 3)
                sweep.append((r * math.cos(a), r * math.sin(a), -0.60 + z_error))
            for k in range(24):  # the lighting scaffold the dolly passes
                sweep.append((2.6, -0.4 + k * 0.05, -0.55 + z_error + k * 0.02))
            writer.add_message(
                channel_id=ch_viz_cloud,
                log_time=t_ns,
                data=point_cloud(t_ns, "lidar_link", sweep),
                publish_time=t_ns,
            )

            entities = []
            if is_drifted:
                entities.append(
                    {
                        "timestamp": stamp(t_ns),
                        "frame_id": "world",
                        "id": "phantom_obstacle",
                        # Messages are 1 Hz, so a sub-second lifetime makes the entity blink
                        # out between frames and the viewer shows nothing.
                        "lifetime": {"sec": 2, "nsec": 0},
                        "frame_locked": False,
                        "cylinders": [
                            {
                                "pose": {
                                    "position": {"x": px + 0.9, "y": 2.0, "z": 0.35},
                                    "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                                },
                                "size": {
                                    "x": costmap_data["inflation_radius_m"] * 2,
                                    "y": costmap_data["inflation_radius_m"] * 2,
                                    "z": 1.2,
                                },
                                "bottom_scale": 1.0,
                                "top_scale": 1.0,
                                "color": {"r": 0.97, "g": 0.30, "b": 0.30, "a": 0.85},
                            }
                        ],
                        "texts": [
                            {
                                "pose": {
                                    "position": {"x": px + 0.9, "y": 2.0, "z": 1.0},
                                    "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                                },
                                "billboard": True,
                                "font_size": 0.22,
                                "scale_invariant": False,
                                "color": {"r": 1.0, "g": 0.6, "b": 0.6, "a": 1.0},
                                "text": "phantom obstacle (stale TF)",
                            }
                        ],
                    }
                )
            writer.add_message(
                channel_id=ch_viz_scene,
                log_time=t_ns,
                data=json.dumps({"deletions": [], "entities": entities}).encode("utf-8"),
                publish_time=t_ns,
            )

        writer.finish()
    return output_path
