# Changelog

## v2.0.0 — MCP-native agent

The investigation is no longer a fixed pipeline with a model bolted on. Gemini
chooses every tool call, and every call travels over the Model Context Protocol.

### Added

- **`MCPGeminiAgent`** (`backend/app/agents/mcp_agent.py`) — a Gemini
  function-calling loop. The model is handed the MCP tool catalogue and decides
  what to call and in what order, up to a 12-round budget. `stream()` yields each
  trace entry the moment it happens, so the console shows the agent's live
  decision log rather than a replay.
- **`MCPToolRouter`** (`backend/app/mcp/router.py`) — MCP client managing stdio
  sessions to every allowed server, aggregating tool catalogues and converting
  each tool's JSON Schema into a Gemini function declaration.
- **First-party MCP server** (`backend/mcp_servers/cineops_mcp.py`) exposing six
  tools: `inspect_mcap_recording`, `search_incident_history`,
  `archive_evidence_to_gcs`, `foxglove_upload_recording`,
  `foxglove_list_recordings`, `foxglove_create_event`. Foxglove's own MCP server
  is a local-only desktop feature that controls the viewer, not the Data
  Platform, so it cannot serve a Cloud Run agent — this wraps the Data Platform
  API in a real MCP server instead of calling it directly.
- **Official `grafana/mcp-grafana` v1.2.0** compiled into the container image and
  spawned over stdio. Its 76 tools are allowlisted down to five observability
  tools so the prompt stays focused.
- `FoxgloveClient` for the Foxglove Data Platform: resolve or create a device,
  request a signed upload link, PUT the `.mcap`, list ingested recordings.
- `scripts/seed_loki.py` — pushes the synthetic Stage A log stream to Grafana
  Cloud Loki so real-mode LogQL queries return live data.
- `scripts/build_demo_video.py` — narration-first demo video build.
- README in English, Korean and Chinese.

### Changed

- **The agent's verdict now drives the UI.** Its ranked hypotheses, recovery
  actions, delay estimate and root-cause summary replace the fixture. Previously
  the single Gemini response was logged and discarded while the console showed
  fixture values.
- **The SSE trace stream runs the agent.** `/incidents/stream-trace` ran the
  deterministic state machine unconditionally, so the agentic path never reached
  the UI even in real mode.
- Grafana datasource UIDs are configurable (`GRAFANA_PROM_DS_UID`,
  `GRAFANA_LOKI_DS_UID`), defaulting to the Grafana Cloud names. They were
  hardcoded to `prometheus`/`loki`, so every real query 404'd and silently fell
  back to the mock client.
- Loki queries send an explicit lookback window (`GRAFANA_LOKI_LOOKBACK_DAYS`,
  default 7). Loki's `query_range` defaults to one hour, shorter than a shoot day.
- Step 7 of the deterministic path now archives the recording to GCS and uploads
  it to Foxglove. `GCSClient` was constructed but `upload_recording()` had no
  call site.
- Failed MCP tool calls are reported as failures. A tool that raised came back as
  an `"Error executing tool ..."` payload rather than an error flag, so the trace
  showed it as successful and the model was not clearly told to retry.
- The live trace badge counts tool calls instead of progress toward a fixed 11
  steps, since the agent decides how many calls to make.
- `ToolTraceEntry.tool_type` gained `foxglove` and `gcs`.

### Notes

- Mock mode, an unreachable MCP server and an unparseable verdict all fall back
  to the deterministic state machine, so offline demos stay reproducible.
- The agent has no actuation tool. Reloading a calibration profile remains a
  recommendation gated on an operator's signature and rollback plan.

## v1.0.0 — Initial release

Deterministic 11-step investigation over synthetic virtual production telemetry,
with a React console, human approval gate, and Grafana/BigQuery/GCS/MCAP clients.
