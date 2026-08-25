# CineOps Guardian — Demo Runbook & Evaluation Guide

This guide provides a **step-by-step walkthrough** for judges, operators, and evaluators to experience CineOps Guardian in under 3 minutes.

---

## 1. Quick Launch (Zero-Prerequisites)

```bash
# 1. Clone repository
git clone https://github.com/chquandogong/cineops-guardian.git
cd cineops-guardian

# 2. Install dependencies (Python 3.12+ and Node 20+)
make install

# 3. Start unified dev server
make dev
```

Open **`http://localhost:5173`** (or `http://localhost:8080` if running unified server).

---

## 2. Interactive Incident Demonstration Flow

### Step 1: Observe the Initial Virtual Production Incident
- Observe the top stage header: **`Scene 42 Take 3`**, **`STAGE PAUSED (INCIDENT)`**, **`P1-CRITICAL`**.
- Review the telemetry cards:
  - **Camera FPS:** Degraded to `16.20 fps` (32.5% frames dropped).
  - **Nav Loops:** `7` recovery retries firing.
  - **TF Checksum:** `TF CHECKSUM MISMATCH (0x3E12 vs 0x8F4A expected)`.
  - **Financial Burn Rate:** `$25,000 / hr` crew downtime cost.

### Step 2: Inspect Multi-Source Telemetry Evidence
- **2D Spatial Path Tab:** View the planned cyan trajectory vs the green/amber/red actual dolly trajectory with avoidance oscillation near **Lighting C-Stand 03**.
- **Prometheus Metrics Tab:** Observe real-time charts for frame delivery collapse, recovery loops, and TF extrinsics error norm.
- **Loki Logs Tab:** Search and filter correlated logs from `tf2_ros_broadcaster`, `costmap_2d`, and `nav2_controller`.
- **Foxglove & BigQuery Tab:** Download the synthetic `.mcap` recording file or inspect past similar incidents.

### Step 3: Trigger Live AI Agent Investigation
- Click the **`Re-Run Agent`** button in the header.
- Watch the right-hand **Agent Investigation Trace** stream in real-time across all 11 diagnostic steps via Server-Sent Events (SSE).
- Click on any step to expand and inspect the tool parameters, duration, and extracted telemetry evidence.

### Step 4: Review Ranked Root-Cause Hypotheses
- **Hypothesis 1 (88% Confidence — Supported):** Stale LiDAR / Camera TF Extrinsic Calibration After Rig Swap (+35mm Z-drift).
- **Hypothesis 2 (12% Confidence — Rejected):** Network Congestion (Ruled out: 0.10% packet loss, 2.4ms RTT).
- **Hypothesis 3 (8% Confidence — Rejected):** GPU Thermal Throttling (Ruled out: 62.5°C steady).

### Step 5: Engage the Human Safety Gate & Authorize Recovery
- Click **`Review & Authorize Action`** on the recovery recommendation card.
- In the safety modal, check the mandatory safety confirmation checkbox and enter your operator name / call sign.
- Click **`Authorize & Execute Recovery`**.

### Step 6: Verify Automatic Post-Action Resolution
- Observe the instant state transition:
  - **Stage Status:** Changes to **`TAKE ACTIVE (RESOLVED)`**.
  - **Camera FPS:** Restores to **`24.00 fps`** (0% dropped frames).
  - **Nav Loops:** Drops to **`0`**.
  - **TF Checksum:** Restores to **`VALID (CRC 0x8F4A)`**.
  - **Estimated Delay:** Reduced from 18m to **4m**, saving Scene 42 Take 3.
