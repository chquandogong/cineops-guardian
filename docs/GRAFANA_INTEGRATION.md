# CineOps Guardian — Grafana MCP & Observability Integration

## 1. Overview & Grafana Labs Partner Track Alignment

**CineOps Guardian** leverages the official [Grafana Model Context Protocol (MCP) Server](https://github.com/grafana/mcp-grafana) (`grafana/mcp-grafana`) as the foundational observability plane connecting runtime virtual production telemetry to the **Gemini 3.7 Flash** reasoning engine.

By exposing Prometheus timeseries metrics, Loki structured log streams, firing alert rules, and dashboard metadata directly to the diagnostic state machine via standardized MCP tool calls, CineOps Guardian enables autonomous yet fully traceable incident root-cause localization.

---

## 2. Supported Telemetry Sources & Metrics Schema

### 2.1. Prometheus Metrics

| Metric Name | Type | Description | Nominal Baseline | Incident Threshold |
|---|---|---|---|---|
| `nav_recovery_loop_count` | Counter | Consecutive Nav2 recovery loops executed | `0` | `> 3` (FIRING at `7`) |
| `camera_delivery_fps` | Gauge | Active camera video delivery frame rate | `24.00 fps` | `< 23.00 fps` (DEGRADED at `16.20 fps`) |
| `tf_extrinsics_error_norm` | Gauge | L2 norm distance between active and approved TF extrinsics | `< 0.005 m` | `> 0.010 m` (CORRUPTED at `0.038 m`) |
| `network_packet_loss_ratio` | Gauge | Stage Private 5G packet loss percentage | `< 0.5%` | `> 2.0%` (NOMINAL at `0.10%`) |
| `gpu_temp_celsius` | Gauge | Onboard Jetson Orin AGX GPU core temperature | `< 70.0°C` | `> 85.0°C` (NOMINAL at `62.5°C`) |
| `gpu_utilization_pct` | Gauge | Onboard video encoding & inference GPU load | `< 75.0%` | `> 95.0%` (NOMINAL at `64.0%`) |

### 2.2. Loki LogQL Stream Queries

CineOps Guardian executes LogQL queries against virtual production stage service streams:

```logql
# Query for TF mismatch and controller recovery behaviors on Stage A
{stage="stage-a"} |= "checksum mismatch" or "recovery behavior"
```

**Log Format Sample:**
```json
{
  "timestamp": "14:21:48.330Z",
  "level": "WARN",
  "service": "tf2_ros_broadcaster",
  "message": "Static transform checksum mismatch for [camera_optical_frame] -> [lidar_link]. Expected CRC 0x8F4A, active 0x3E12.",
  "labels": {
    "stage": "stage-a",
    "frame_id": "camera_optical_frame",
    "parent_id": "lidar_link"
  }
}
```

---

## 3. Grafana MCP Tool Registry & Client Architecture

The backend implements `GrafanaMCPClient` ([`backend/app/integrations/grafana/mcp_client.py`](file:///home/chquan/work/cineops-guardian/backend/app/integrations/grafana/mcp_client.py)) supporting dual operating modes:

1. **`DEMO_MODE=mock` (Offline / Hermetic):** Fully deterministic, fast, zero-dependency fixtures for development, testing, and offline hackathon evaluation.
2. **`DEMO_MODE=real` (Live Cloud):** Direct HTTP / MCP calls to Grafana Cloud stack endpoints authenticated via service account tokens.

### MCP Tool Methods

```python
class GrafanaMCPClient:
    async def get_alert_rules(self, stage_id: str) -> list[dict[str, Any]]:
        """Queries active alert definitions and firing state."""

    async def query_prometheus(self, query: str, time_range: str = "5m") -> dict[str, Any]:
        """Executes instant or range Prometheus PromQL queries."""

    async def query_loki(self, logql: str, limit: int = 10) -> list[dict[str, Any]]:
        """Queries structured Loki log streams matching LogQL expressions."""

    async def search_dashboards(self, query: str = "stage-a") -> list[dict[str, Any]]:
        """Searches stage dashboard UID and panel deep links."""
```

---

## 4. Live Grafana Cloud Setup Instructions

To connect CineOps Guardian to your live Grafana Cloud instance:

1. Generate a **Grafana Cloud Service Account Token** with `Alerts:Read`, `DataSources:Query`, and `Dashboards:Read` permissions.
2. Update `.env`:
   ```bash
   DEMO_MODE=real
   GRAFANA_URL=https://your-stack.grafana.net
   GRAFANA_SERVICE_ACCOUNT_TOKEN=glsa_your_service_account_token
   GRAFANA_MCP_URL=http://localhost:8000
   ```
3. Run the application:
   ```bash
   make dev
   ```
