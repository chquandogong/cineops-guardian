# Changelog

## v2.3.0 — the incident leaves the process

### Changed

- **`IncidentStore` replaces module-level state.** The incident under
  investigation used to be a field on a singleton service object, so the service
  had to run pinned to `--max-instances 1`. Two backends now sit behind one
  interface: `memory` for local runs and mock mode, `firestore` for the deployed
  service — one document per incident id, written after every streamed step.
  Firestore being unreachable degrades to memory with a warning rather than
  failing startup, and `/health` reports which backend won.
- The service runs `--max-instances 4`.

### Added

- **`X-Instance-Id` on every response**, resolved once per process from the Cloud
  Run metadata server and degrading to a process id off Cloud Run. Shared state is
  a claim until you can tell the instances apart.

### Verified

The first version of this test proved nothing: all 73 concurrent reads landed on
the writer's own instance, because Cloud Run fits 80 concurrent requests in one
container. Pinning container concurrency to 1 makes the SSE stream occupy one
instance for its whole run, so every reader is necessarily elsewhere. Measured on
the deployed service, writer on `4ec7015b5fd3`:

| round | steps streamed | trace length seen by readers | reader instances |
|---|---|---|---|
| 0 | 1 | 1 | `d2341ec2d7ad`, `e3aba124b4ce`, `ea2753a960e4` |
| 1 | 6 | 6 | `d2341ec2d7ad`, `e3aba124b4ce`, `ea2753a960e4` |
| 3 | 10 | 10 | `d2341ec2d7ad`, `e3aba124b4ce` |
| 5 | 14 | 14 | `d2341ec2d7ad`, `e3aba124b4ce` |

Three instances that never ran the agent tracked the investigation step for step,
and the finished 16-step trace read back identically.


## v2.2.0 — a baseline that binds, and a recording that renders

### Added

- **`compare_with_baseline`** MCP tool. Generates a nominal reference take of the
  same rig on the same route, renders both paths side by side on a shared scale,
  and returns a metric-by-metric split of what is identical and what differs.
  A measurement only becomes an anomaly next to a baseline.
- **Ablation test for it.** `BASELINE_TF_Z` sets what the reference rig settles
  on. Point it at the failing take's own value and every metric comes back
  identical, which must change the verdict. Measured on the deployed service:

  | | clean baseline | ablation baseline |
  |---|---|---|
  | primary hypothesis | Stale TF Extrinsic Drift | Unexplained Trajectory Halt |
  | confidence / status | 0.98 supported | 0.30 investigating |
  | TF hypothesis | rank 1 | demoted to rank 2, rejected |
  | guardrail | did not fire | fired |

- **`_flag_baseline_contradiction` guardrail.** The first ablation run *failed*:
  the tool correctly reported `differing_metrics: {}` and the agent blamed TF
  drift at 0.95 anyway, dropping the baseline from its evidence. Prompting is not
  a control, so the verdict is now checked against what the baseline returned
  regardless of whether the model cooperated — the trace gains an error entry, the
  hypothesis drops to `investigating`, confidence is capped at 0.30 and the
  contradiction is added to missing_evidence.
- **Well-known Foxglove schemas.** `foxglove.FrameTransform`, `PoseInFrame`,
  `PointCloud` and `SceneUpdate` on four visualization topics: the full TF tree
  carrying the drifting Z, the dolly pose, a LiDAR sweep projected with the
  calibration error applied, and the phantom obstacle as scene geometry.
- **`operator_link`** on the Foxglove tool payloads, carrying `FOXGLOVE_LAYOUT_ID`
  and the flagged timestamp.
- **Order-of-events strip** on the rendered frame, naming each transition and the
  gap between them.

### Fixed

- **Uploading to Foxglove produced an empty viewer.** The 3D panel does not draw
  arbitrary JSON; a bag made entirely of `foxglove.JsonMessage` on custom topics
  loads without error and shows nothing. The operator handoff this project
  advertised did not exist. Verified fixed in the viewer: ground grid, LiDAR
  point cloud and the labelled `world → base_link → lidar_link →
  camera_optical_frame` tree all render.
- **A bare recordings URL opened the default layout**, whose panels have no topics
  enabled — so even a correct bag showed nothing. Links now open the
  incident-triage layout at the annotated moment.
- **Scene entities blinked out.** Lifetime was 0.4s against 1 Hz messages, so the
  phantom obstacle never appeared between frames.
- **The Grafana MCP binary was recompiled from source on every deploy.** Cloud
  Build keeps no layer cache, and once Pillow joined the dependency set the build
  ran past its timeout and started failing. The runtime stage now downloads the
  published v1.2.0 release and verifies it with `--version`, dropping a whole
  builder stage.

### Verified

Side-by-side plots in Foxglove showed something a min/max table hides: the
transform diverges at t=10s and the frame rate only falls at t=12s. That ordering
is now stated on the rendered frame, and the model cites it:

> "Order of events shows TF Z divergence at t=10s, followed by frame rate dropping
> to 16.20 fps at t=12s, and recovery loops beginning at t=14s."

### Not done, and why

The Foxglove viewer needs an authenticated browser session; an API key does not
authenticate the web app. Capturing its screen server-side would mean storing a
session cookie in a deployed service — fragile and a poor security trade. The
information the viewer contributed (3D geometry, causal ordering) is delivered
through the rendered frame instead, and the operator gets the real viewer via the
layout link.

## v2.1.0 — the agent looks at the telemetry

The agent reasoned only over summary statistics. An oscillating avoidance loop is
a *shape* — a smooth traverse that collapses into a tight zig-zag at one specific
point — obvious to a rig operator at a glance, easy to miss in a min/max table.

### Added

- **`render_spatial_evidence`** MCP tool. Draws the ROS2 MCAP telemetry
  server-side and returns MCP **image content**: a top-down view of the dolly path
  against the costmap inflation blocking it, the TF Z-translation against its
  approved value, and camera frame rate against target.
- **Image transport through the whole chain.** `MCPToolRouter.call()` now returns
  an `MCPCallResult` carrying decoded image bytes alongside the text, and the
  agent attaches them to the model turn as inline image parts — a rendered frame
  cannot ride inside a function response.
- `MCAPInspector.read_channels()`, so the summary and the render share one pass
  over the file.
- Pillow dependency. Rendering is pure Pillow with Pillow's scalable default
  font: no plotting stack, no system font dependency in `python:slim`, and
  deterministic output so the offline demo still reproduces.

### Changed

- The agent prompt asks the model to say where the path stops being smooth and
  what it is avoiding when it does — and explicitly not to describe an image it
  was not shown.

### Verified

On the deployed service the model called `render_spatial_evidence` unprompted at
step 4 and cited what it saw in its own supporting evidence:

> "Rendered spatial frame shows linear nominal cyan trajectory breaking into tight
> amber zig-zag recovery loops centered around phantom obstacle"

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
