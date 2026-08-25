# CineOps Guardian — Hackathon Submission Details

## Project Summary

| Parameter | Value |
|---|---|
| **Project Title** | **CineOps Guardian** |
| **Short Description** | AI-Powered Observability & Incident Recovery Agent for Virtual Production Stages & Robotic Camera Fleets |
| **Track Alignment** | **Agentic Cinema & Observability** (Grafana Labs Partner Track) |
| **Primary Model** | **Gemini 3.7 Flash** (Thinking Level: `HIGH`) |
| **Observability Integration** | **Grafana MCP Server (`grafana/mcp-grafana`)** |
| **Telemetry & Robotics** | **Foxglove Studio MCAP**, ROS2 Iron (`tf2_ros`, `nav2_costmap`), BigQuery |
| **License** | Apache 2.0 |
| **Author** | Chenghao Quan (`chquan17@gmail.com`) |

---

## 1. Problem Statement & Real-World Impact

Modern cinema and high-end episodic production increasingly rely on **Virtual Production (VP) LED Volumes** driven by Unreal Engine nDisplay and precision robotic motion-control camera rigs.

When a camera tracking anomaly or sensor extrinsics drift occurs mid-take:
- Camera tracking diverges from LED wall background parallax.
- Costmaps miscalculate physical clearance, causing dollies to jerk into emergency recovery loops.
- Production halts with full sound stage crews, actors, and director waiting, incurring downtime costs of **$20,000 to $50,000 per hour**.
- Manual troubleshooting requires disparate log grep, ROS TF inspection, and network sniffing, taking 20–45 minutes.

---

## 2. Our Solution: CineOps Guardian

CineOps Guardian is an autonomous observability agent that:
1. **Instantly Ingests Stage Incidents:** Triages stage anomalies within 50ms.
2. **Queries Grafana MCP:** Extracts Prometheus timeseries metrics and Loki log streams in real-time.
3. **Inspects Spatial MCAP Recordings:** Examines multi-channel ROS2/Foxglove `.mcap` files to uncover coordinate translation errors down to the millimeter.
4. **Applies Gemini 3.7 Flash High-Thinking:** Formulates, differentially tests, and ranks physical hypotheses with mathematical rigor.
5. **Enforces Human-in-the-Loop Safety Interlocks:** Strictly requires authorized operator sign-off before applying any configuration fix.
6. **Empirically Verifies Recovery:** Automates 4-point post-action telemetry re-testing to certify stage readiness before resuming filming.

---

## 3. Technology Architecture & Integration Highlights

- **Gemini 3.7 Flash (High Thinking):** Utilizes Google's state-of-the-art reasoning model via the official `google-genai` SDK with strict JSON schema outputs and extended thinking budgets.
- **Official Grafana MCP Integration:** Implements runtime client tooling for Prometheus PromQL queries, Loki LogQL streaming, alert definitions, and dashboard discovery.
- **Foxglove MCAP Telemetry:** Generates and parses real `.mcap` binary recordings with JSON schemas for `/tf`, `/dolly/odom`, `/costmap/obstacles`, and `/camera/status`.
- **Google Cloud BigQuery & GCS:** Stores synthetic historical incident knowledge graphs and cloud recording archives.
- **React 18 + Tailwind Operator Console:** Interactive stage console featuring custom HTML5 Canvas trajectory rendering, live SSE trace streaming, and safety gates.

---

## 4. Compliance & Synthetic Data Certification

- **Zero Proprietary Data:** 100% of telemetry, logs, MCAP recordings, and incident scenarios are procedurally generated synthetic fixtures.
- **Zero Robot Danger:** The agent has zero direct robot actuation APIs; recovery actions are restricted to configuration and calibration snapshots.
