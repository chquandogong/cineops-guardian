from typing import Any


class MockGrafanaMCPClient:
    """Deterministic high-fidelity mock client providing exact Grafana MCP tool responses."""

    def __init__(self):
        self.connected = True

    async def get_alert_rules(self, stage_id: str = "stage-a") -> list[dict[str, Any]]:
        return [
            {
                "name": "CameraDollyOscillation",
                "state": "firing",
                "severity": "critical",
                "condition": "rate(nav_recovery_loop_count[1m]) > 2",
                "value": 7.0,
                "summary": "Robotic camera dolly entered repeated avoidance recovery loops on Stage A.",
                "labels": {
                    "stage": "stage-a",
                    "asset": "dolly-alpha-01",
                    "service": "nav2_controller",
                },
                "fired_at": "2026-08-25T14:22:03Z",
            },
            {
                "name": "CameraGenlockFrameDrop",
                "state": "firing",
                "severity": "warning",
                "condition": "camera_delivery_fps < 23.5",
                "value": 16.2,
                "summary": "Optical tracking camera frame delivery rate dropped to 16.20 fps.",
                "labels": {
                    "stage": "stage-a",
                    "camera": "ARRI_Alexa_Mini_LF",
                    "service": "camera_streamer",
                },
                "fired_at": "2026-08-25T14:22:04Z",
            },
        ]

    async def query_prometheus(self, query: str, time_range: str = "5m") -> dict[str, Any]:
        if "recovery" in query:
            return {
                "status": "success",
                "query": query,
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {
                            "__name__": "nav_recovery_loop_count",
                            "asset": "dolly-alpha-01",
                        },
                        "values": [
                            [1724595700, "0"],
                            [1724595710, "1"],
                            [1724595720, "4"],
                            [1724595730, "7"],
                        ],
                    }
                ],
            }
        elif "fps" in query or "camera" in query:
            return {
                "status": "success",
                "query": query,
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"__name__": "camera_delivery_fps", "asset": "dolly-alpha-01"},
                        "values": [
                            [1724595700, "24.0"],
                            [1724595710, "23.8"],
                            [1724595720, "19.4"],
                            [1724595730, "16.2"],
                        ],
                    }
                ],
            }
        elif "tf" in query:
            return {
                "status": "success",
                "query": query,
                "resultType": "vector",
                "result": [
                    {
                        "metric": {
                            "__name__": "tf_extrinsics_error_norm",
                            "frame": "camera_optical_frame",
                        },
                        "value": [1724595730, "0.038"],
                    }
                ],
            }
        elif "packet_loss" in query or "network" in query:
            return {
                "status": "success",
                "query": query,
                "resultType": "vector",
                "result": [
                    {
                        "metric": {"__name__": "network_packet_loss_ratio", "interface": "wlan0"},
                        "value": [1724595730, "0.001"],
                    }
                ],
            }
        return {"status": "success", "query": query, "result": []}

    async def query_loki(self, logql: str, limit: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "timestamp": "14:21:45.102Z",
                "labels": {"stage": "stage-a", "service": "dolly-rig-mgr"},
                "line": "Lens swap acknowledged: CinePrime 35mm T1.5 mounted on Camera Dolly Alpha.",
            },
            {
                "timestamp": "14:21:48.330Z",
                "labels": {"stage": "stage-a", "service": "tf2_ros_broadcaster"},
                "line": "Static transform checksum mismatch for [camera_optical_frame] -> [lidar_link]. Expected CRC 0x8F4A, active 0x3E12.",
            },
            {
                "timestamp": "14:22:01.050Z",
                "labels": {"stage": "stage-a", "service": "costmap_2d"},
                "line": "Rapid obstacle inflation detected near coordinates (x: 4.82, y: 2.15). Clearance threshold violated (1.25m < 1.50m).",
            },
            {
                "timestamp": "14:22:03.410Z",
                "labels": {"stage": "stage-a", "service": "nav2_controller"},
                "line": "Navigation recovery behavior entered: [SpinRecovery -> BackupRecovery]. Consecutive retry count: 7.",
            },
            {
                "timestamp": "14:22:04.990Z",
                "labels": {"stage": "stage-a", "service": "camera_streamer"},
                "line": "Frame delivery degradation: 32.5% frames dropped in last 5000ms. Optical genlock jitter exceeded 18ms.",
            },
        ]

    async def search_dashboards(self, query: str = "stage-a") -> list[dict[str, Any]]:
        return [
            {
                "uid": "stage-a-dolly",
                "title": "Stage A — Robotic Dolly & Camera Observability",
                "url": "/d/stage-a-dolly/camera-dolly-stage-a",
                "tags": ["virtual-production", "robotics", "stage-a"],
                "isStarred": True,
            }
        ]
