#!/usr/bin/env python3
"""Pushes synthetic CineOps stage telemetry logs into Grafana Cloud Loki."""

import base64
import json
import os
import time
import urllib.request

LOKI_URL = os.environ["LOKI_URL"]  # https://logs-prod-030.grafana.net/loki/api/v1/push
LOKI_USER = os.environ["LOKI_USER"]  # instance id
LOKI_TOKEN = os.environ["LOKI_TOKEN"]  # glc_...

ENTRIES = [
    (
        "INFO",
        "dolly-rig-mgr",
        "Lens swap acknowledged: CinePrime 35mm T1.5 mounted on Camera Dolly Alpha.",
    ),
    (
        "WARN",
        "tf2_ros_broadcaster",
        "Static transform checksum mismatch for [camera_optical_frame] -> [lidar_link]. Expected CRC 0x8F4A, active 0x3E12.",
    ),
    (
        "WARN",
        "costmap_2d",
        "Rapid obstacle inflation detected near coordinates (x: 4.82, y: 2.15). Clearance threshold violated (1.25m < 1.50m).",
    ),
    (
        "ERROR",
        "nav2_controller",
        "Navigation recovery behavior entered: [SpinRecovery -> BackupRecovery]. Consecutive retry count: 7.",
    ),
    (
        "ERROR",
        "camera_streamer",
        "Frame delivery degradation: 32.5% frames dropped in last 5000ms. Optical genlock jitter exceeded 18ms.",
    ),
]

now = time.time_ns()
streams = []
for i, (level, service, msg) in enumerate(ENTRIES):
    ts = str(now - (len(ENTRIES) - i) * 2_000_000_000)  # 2s apart, ending ~now
    streams.append(
        {
            "stream": {
                "stage": "stage-a",
                "asset": "dolly-alpha-01",
                "service": service,
                "level": level,
                "scene_take": "scene-42-take-3",
                "source": "cineops-guardian-synthetic",
            },
            "values": [[ts, msg]],
        }
    )

body = json.dumps({"streams": streams}).encode()
auth = base64.b64encode(f"{LOKI_USER}:{LOKI_TOKEN}".encode()).decode()
req = urllib.request.Request(
    LOKI_URL,
    data=body,
    method="POST",
    headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("PUSH status:", r.status, r.read(200).decode() or "(empty)")
except urllib.error.HTTPError as e:
    print("PUSH HTTPError:", e.code, e.read(400).decode())
except Exception as e:
    print("PUSH error:", repr(e))
