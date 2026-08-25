# AGENTS.md — CineOps Guardian Agent Guidance & Operating Manual

Welcome to **CineOps Guardian**, the AI-powered incident investigation and recovery platform for virtual production stages and robotic camera platforms.

## Core Directives for Autonomous & Pair Agents

1. **AI Technology Stack:**
   - Use only Google AI technologies (`gemini-3.7-flash`, thinking level `HIGH`) via `google-adk` / `google-genai`.
   - Never introduce OpenAI, Anthropic, Claude, LangChain, LlamaIndex, or other 3rd party AI frameworks.

2. **Observability & Grafana MCP:**
   - Active runtime integration with `grafana/mcp-grafana`.
   - All MCP tool calls (Prometheus metrics, Loki logs, alert rules, dashboards) must be transparently exposed in the agent trace.
   - Dual-mode support:
     - `DEMO_MODE=mock`: Hermetic, deterministic fixtures for local offline development.
     - `DEMO_MODE=real`: Live calls to Grafana Cloud MCP, Gemini 3.7 Flash, BigQuery, and GCS.

3. **Domain Rigor (Entertainment & Virtual Production):**
   - Maintain accurate domain terminology: camera dolly, optical tracker, static transform (`tf2_ros`), URDF, LiDAR point cloud, costmap obstacle inflation, nav recovery loop, LED wall genlock, timecode, scene/take.
   - Ground all hypotheses in physical reality and empirical telemetry evidence.

4. **Safety & Human Oversight:**
   - Never attempt to actuate physical robots or bypass stage safety interlocks.
   - All recovery actions require explicit operator review, rollback procedures, and post-action verification criteria.

5. **No Proprietary Leaks:**
   - Ensure 100% synthetic telemetry and test fixtures. Zero proprietary assets, company-internal logs, or customer secrets.

