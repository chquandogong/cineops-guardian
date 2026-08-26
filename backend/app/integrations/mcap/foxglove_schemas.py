"""Well-known Foxglove schemas, so a recording renders instead of sitting empty.

Foxglove's 3D panel does not draw arbitrary JSON. It looks for the well-known
schema names — `foxglove.FrameTransform`, `foxglove.PoseInFrame`,
`foxglove.PointCloud`, `foxglove.SceneUpdate` — and renders the geometry they
describe. A bag full of `foxglove.JsonMessage` on custom topics loads fine and
shows nothing, which is exactly the state this project shipped in until now.

These are the JSON-encoded variants: schema `encoding="jsonschema"`, message
`message_encoding="json"`. That keeps the recording readable by hand while still
driving the viewer.

Reference: https://docs.foxglove.dev/docs/visualization/message-schemas/introduction
"""

import base64
import json
import math
import struct
from typing import Any

TIME = {
    "type": "object",
    "properties": {"sec": {"type": "integer"}, "nsec": {"type": "integer"}},
}
VEC3 = {
    "type": "object",
    "properties": {
        "x": {"type": "number"},
        "y": {"type": "number"},
        "z": {"type": "number"},
    },
}
QUAT = {
    "type": "object",
    "properties": {
        "x": {"type": "number"},
        "y": {"type": "number"},
        "z": {"type": "number"},
        "w": {"type": "number"},
    },
}
POSE = {"type": "object", "properties": {"position": VEC3, "orientation": QUAT}}
COLOR = {
    "type": "object",
    "properties": {
        "r": {"type": "number"},
        "g": {"type": "number"},
        "b": {"type": "number"},
        "a": {"type": "number"},
    },
}

FRAME_TRANSFORM = {
    "type": "object",
    "properties": {
        "timestamp": TIME,
        "parent_frame_id": {"type": "string"},
        "child_frame_id": {"type": "string"},
        "translation": VEC3,
        "rotation": QUAT,
    },
}

POSE_IN_FRAME = {
    "type": "object",
    "properties": {"timestamp": TIME, "frame_id": {"type": "string"}, "pose": POSE},
}

POINT_CLOUD = {
    "type": "object",
    "properties": {
        "timestamp": TIME,
        "frame_id": {"type": "string"},
        "pose": POSE,
        "point_stride": {"type": "integer"},
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "offset": {"type": "integer"},
                    "type": {"type": "integer"},
                },
            },
        },
        "data": {"type": "string", "contentEncoding": "base64"},
    },
}

SCENE_UPDATE = {
    "type": "object",
    "properties": {
        "deletions": {"type": "array", "items": {"type": "object"}},
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": TIME,
                    "frame_id": {"type": "string"},
                    "id": {"type": "string"},
                    "lifetime": TIME,
                    "frame_locked": {"type": "boolean"},
                    "cylinders": {"type": "array", "items": {"type": "object"}},
                    "cubes": {"type": "array", "items": {"type": "object"}},
                    "spheres": {"type": "array", "items": {"type": "object"}},
                    "lines": {"type": "array", "items": {"type": "object"}},
                    "texts": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
    },
}

FLOAT32 = 7  # foxglove.PackedElementField.NumericType

SCHEMAS: dict[str, dict[str, Any]] = {
    "foxglove.FrameTransform": FRAME_TRANSFORM,
    "foxglove.PoseInFrame": POSE_IN_FRAME,
    "foxglove.PointCloud": POINT_CLOUD,
    "foxglove.SceneUpdate": SCENE_UPDATE,
}


def stamp(ns: int) -> dict[str, int]:
    return {"sec": ns // 1_000_000_000, "nsec": ns % 1_000_000_000}


def quat_from_yaw(yaw_rad: float) -> dict[str, float]:
    return {"x": 0.0, "y": 0.0, "z": math.sin(yaw_rad / 2), "w": math.cos(yaw_rad / 2)}


def pack_points(points: list[tuple[float, float, float]]) -> str:
    """Packs XYZ float32 triples into the base64 payload a PointCloud expects."""
    blob = b"".join(struct.pack("<fff", *p) for p in points)
    return base64.b64encode(blob).decode("ascii")


def point_cloud(ns: int, frame_id: str, points: list[tuple[float, float, float]]) -> bytes:
    return json.dumps(
        {
            "timestamp": stamp(ns),
            "frame_id": frame_id,
            "pose": {
                "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            },
            "point_stride": 12,
            "fields": [
                {"name": "x", "offset": 0, "type": FLOAT32},
                {"name": "y", "offset": 4, "type": FLOAT32},
                {"name": "z", "offset": 8, "type": FLOAT32},
            ],
            "data": pack_points(points),
        }
    ).encode("utf-8")
