# CineOps Guardian — Devpost Submission Package

## 📋 Devpost Submission Form Fields

### 1. Basic Information

- **Project Name:** `CineOps Guardian`
- **Tagline (Elevator Pitch):** `AI-Powered Observability & Incident Recovery Agent for Virtual Production Stages & Robotic Camera Fleets`
- **Partner Track:** `Grafana Labs`
- **GitHub Repository URL:** `https://github.com/chquandogong/cineops-guardian`
- **Release Version / Tag:** `https://github.com/chquandogong/cineops-guardian/releases/tag/v1.0.0`
- **License:** `Apache 2.0 (Open Source)`
- **Video Demo Link:** `[Add Public YouTube / Vimeo Link to 3-Minute Trailer]`

---

### 2. Built With (Tags)

`gemini-3.7-flash`, `google-cloud-platform`, `grafana-mcp`, `prometheus`, `loki`, `mcap`, `foxglove`, `ros2`, `bigquery`, `fastapi`, `react`, `typescript`, `tailwind-css`, `docker`

---

### 3. Submission Essay Questions (Copy-Paste Ready)

#### 🎬 Inspiration
Modern cinema and high-end episodic production are experiencing a massive paradigm shift toward **Virtual Production (VP) LED Volumes** driven by Unreal Engine nDisplay and precision robotic motion-control camera rigs (dollies, cranes, pan-tilt heads). In these environments, physical cameras and digital frustums must be synchronized to sub-millimeter precision and sub-millisecond genlock.

However, film sets are chaotic physical environments. A simple physical adjustment—such as swapping a camera lens without updating the static transform calibration matrix—causes LiDAR point clouds to misalign with optical nodal points. To the autonomous navigation stack, the set floor and lighting scaffolds appear as "phantom obstacles," triggering emergency avoidance loops and dropped video frames.

When a stage halts, an entire crew of 60+ actors, technicians, and directors sits idle, burning **$20,000 to $50,000+ per hour**. Diagnosing these cyber-physical anomalies manually takes 30–60 minutes of tedious log grep and ROS transform inspection. We built **CineOps Guardian** to give stage engineers and rig operators an autonomous observability agent that root-causes and resolves multi-system anomalies in under 60 seconds.

---

#### 🛠️ What it Does
**CineOps Guardian** is an enterprise-grade observability and diagnostic agent built specifically for virtual production and camera robotics:

1. **Instant Incident Triage:** Ingests stage alerts within 50ms, identifying the affected scene (`Scene 42 Take 3`), stage volume, and robotic asset.
2. **Grafana MCP Observability Plane:** Connects to the official `grafana/mcp-grafana` server to execute live PromQL queries (camera FPS, navigation recovery loop counts, TF extrinsics error norm) and Loki LogQL stream queries (CRC checksum mismatches and costmap inflation warnings).
3. **Foxglove MCAP Telemetry Extraction:** Server-side inspection of multi-channel ROS2 `.mcap` binary recordings (`/tf`, `/dolly/odom`, `/costmap/obstacles`, `/camera/status`), mathematically localizing coordinate frame drift down to the millimeter ($+35\text{mm}$ Z-offset).
4. **Gemini 3.7 Flash High-Thinking Reasoning:** Applies Google's flagship reasoning model with an extended thinking budget to differentially evaluate, test, and rank physical root-cause hypotheses while systematically ruling out network packet loss and GPU thermal throttling.
5. **BigQuery Historical Incident Matching:** Searches historical stage incidents to find proven past recovery procedures with high similarity scores ($94\%$).
6. **Human-in-the-Loop Safety Interlocks:** Strictly enforces operator review and authorization before applying configuration snapshots, guaranteeing zero unverified physical robot motion.
7. **Automated Post-Recovery Verification:** Runs an automated 4-point telemetry re-verification checklist to confirm static transform checksum convergence and restore 24.00 fps genlock sync.

---

#### 🏗️ How We Built It
- **AI Core:** Built with Google AI's **Gemini 3.7 Flash** (thinking level `HIGH`) using the official `google-genai` SDK with strict JSON Schema output contracts (`Pydantic v2`).
- **Observability Layer:** Integrated with **Grafana Model Context Protocol (MCP)** supporting Prometheus metrics, Loki log streams, and Grafana Cloud alert definitions.
- **Robotics & Spatial Telemetry:** Implemented Foxglove-compatible `.mcap` serialization and inspection supporting ROS2 sensor fusion channels and static transform trees (`tf2_ros`).
- **Data & Cloud Backend:** **Google Cloud BigQuery** for historical incident matching, **Google Cloud Storage (GCS)** for evidence archiving, and **FastAPI** for the asynchronous diagnostic engine.
- **Frontend Console:** **React 18**, **TypeScript**, **Tailwind CSS**, and custom **HTML5 Canvas 2D spatial trajectory visualizer** with real-time Server-Sent Events (SSE) agent trace streaming.

---

#### 🧗 Challenges We Ran Into
Bridging the gap between cloud-native observability paradigms (Prometheus timeseries, Loki logs) and cyber-physical robotics (rigid-body spatial transforms, URDF models, 2D obstacle inflation maps) presented unique engineering hurdles:
1. **Mathematical Multi-Modal Grounding:** Ensuring the LLM grounded its reasoning in physical reality ($SE(3)$ transformation matrices and LiDAR raycasting) rather than generic software errors.
2. **Strict Operational Safety:** Ensuring the AI assistant operates within a "zero actuation" boundary, restricting its recovery actions to safe configuration and calibration reloads with mandatory human operator signatures.
3. **Hermetic vs. Live Cloud Dual-Mode:** Developing a seamless dual-mode architecture (`DEMO_MODE=mock` and `DEMO_MODE=real`) allowing judges and developers to run 100% offline deterministic fixtures while retaining full live Grafana Cloud MCP connectivity.

---

#### 🏆 Accomplishments That We're Proud Of
- **11-Step Auditable State Machine:** Every single tool call, PromQL query, LogQL filter, and MCAP byte range is surfaced transparently in the live SSE trace with millisecond-accurate execution timing.
- **Sub-Millimeter Physical Accuracy:** Successfully localizing a $+35\text{mm}$ lens nodal shift from multi-channel MCAP telemetry recordings.
- **100% Synthetic Telemetry:** Created 100% procedural synthetic telemetry, test fixtures, and ROS2 bags with zero proprietary dependencies or data leaks.
- **Complete Test Coverage:** 11/11 passing Pytest unit & integration tests, 0 Ruff lint errors, and 100% clean frontend Vite bundle builds.

---

#### 💡 What We Learned
- **The Power of Grafana MCP:** How the Model Context Protocol transforms observability from reactive dashboard browsing into proactive, context-aware diagnostic intelligence.
- **Extended Thinking in Cyber-Physical Systems:** How Gemini 3.7 Flash's thinking capabilities excel at differential diagnosis—systematically evaluating conflicting hypotheses against telemetry evidence before committing to a conclusion.

---

#### 🔮 What's Next for CineOps Guardian
- **Multi-Stage Fleet Orchestration:** Expanding from single-stage monitoring to studio-wide multi-volume fleet management across LED stages.
- **Unreal Engine Live Link Plugin:** Direct telemetry feed from Unreal Engine nDisplay frustum renderers into the CineOps Guardian observability plane.
- **Edge Deployment on NVIDIA Jetson:** Deploying lightweight CineOps Guardian sidecar agents directly onboard motion-control camera rigs for offline edge-level anomaly detection.
