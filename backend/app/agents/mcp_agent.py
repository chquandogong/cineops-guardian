"""Gemini agent loop driven entirely by MCP tools.

Unlike the deterministic state machine, nothing here decides in advance which
telemetry to fetch. Gemini 3.7 Flash is handed the MCP tool catalogue — Grafana
Cloud through the official ``mcp-grafana`` server, and Foxglove / BigQuery / GCS /
MCAP through this project's own MCP server — and chooses what to call, in what
order, until it can commit to a ranked diagnosis.

Every tool call the model makes is recorded as a ``ToolTraceEntry``, so the trace
the operator reads is the agent's actual decision log rather than a script.
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from backend.app.agents.prompts import INVESTIGATION_SYSTEM_PROMPT
from backend.app.agents.schemas import AgentInvestigationOutput
from backend.app.domain.models import Incident, ToolTraceEntry
from backend.app.mcp.router import MCPToolRouter, MCPUnavailableError
from backend.app.settings import settings

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 12
MAX_TOOL_RESULT_CHARS = 6000

# Which trace lane a tool shows up in, so the operator can see at a glance which
# system the agent reached into.
TOOL_TYPE_BY_PREFIX: dict[str, str] = {
    "query_prometheus": "grafana_mcp",
    "query_loki_logs": "grafana_mcp",
    "list_datasources": "grafana_mcp",
    "list_prometheus_metric_names": "grafana_mcp",
    "list_loki_label_names": "grafana_mcp",
    "search_incident_history": "bigquery",
    "inspect_mcap_recording": "mcap_inspector",
    "render_spatial_evidence": "mcap_inspector",
    "archive_evidence_to_gcs": "gcs",
    "foxglove_upload_recording": "foxglove",
    "foxglove_list_recordings": "foxglove",
    "foxglove_create_event": "foxglove",
}

AGENT_TASK_PROMPT = """\
Stage A of a virtual production LED volume has halted. Incident {incident_id} is \
open on robotic camera dolly {robot_id} during {scene} {take}. Firing alerts: \
CameraDollyOscillation and CameraGenlockFrameDrop. Every minute of downtime costs \
the production about $25,000/hr, so work quickly but never guess.

You have MCP tools for Grafana Cloud (Prometheus metrics and Loki logs), the \
BigQuery incident history, the Google Cloud Storage evidence archive, the ROS2 \
MCAP recording inspector, and the Foxglove Data Platform.

Investigate on your own initiative:

1. Pull the telemetry and logs you actually need. Discover datasource UIDs rather \
than assuming them; if a query comes back empty, say so instead of inventing values.
2. Measure the physical evidence in the MCAP recording before claiming a spatial \
root cause. Quote the numbers the tool returns.
3. Render that telemetry and *look at the frame*. Say what the path actually looks \
like — where it stops being smooth, and what it is avoiding when it does. Do not \
describe an image you were not shown.
4. Check whether this has happened before and what fixed it.
5. Actively rule out the plausible alternatives (network congestion, GPU thermal \
throttling) against telemetry, and mark them rejected with the conflicting evidence.
6. Preserve the evidence: archive the recording and publish it to Foxglove so a rig \
operator can scrub the real bag, and annotate the incident on the Foxglove timeline.

Then stop calling tools and return the final structured investigation. Ground every \
number in a tool result you actually received. If something could not be measured, \
list it under missing_evidence rather than filling it in.
"""


def _trace_type(tool_name: str) -> str:
    return TOOL_TYPE_BY_PREFIX.get(tool_name, "system")


def _truncate(text: str, limit: int = MAX_TOOL_RESULT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n…[truncated {len(text) - limit} chars]"


def _summarize(text: str, limit: int = 220) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


class MCPGeminiAgent:
    """Runs one investigation as a Gemini function-calling loop over MCP."""

    def __init__(self, incident: Incident):
        self.incident = incident
        self.traces: list[ToolTraceEntry] = []
        self.verdict: AgentInvestigationOutput | None = None
        self._step = 0

    def _next_step(self) -> int:
        self._step += 1
        return self._step

    def _record(
        self,
        *,
        step_name: str,
        tool_type: str,
        action_summary: str,
        tool_name: str,
        tool_input: dict[str, Any],
        output_summary: str,
        duration_ms: int,
        status: str = "success",
    ) -> None:
        self.traces.append(
            ToolTraceEntry(
                step_number=self._next_step(),
                step_name=step_name,
                tool_type=tool_type,  # type: ignore[arg-type]
                action_summary=action_summary,
                tool_name=tool_name,
                tool_input_safe=tool_input,
                tool_output_summary=output_summary,
                timestamp=datetime.now(UTC).isoformat(),
                duration_ms=duration_ms,
                status=status,  # type: ignore[arg-type]
            )
        )

    async def run(self) -> tuple[list[ToolTraceEntry], AgentInvestigationOutput | None]:
        """Runs the agent to completion. Returns (trace, structured verdict or None)."""
        async for _ in self.stream():
            pass
        return self.traces, self.verdict

    async def stream(self) -> AsyncGenerator[ToolTraceEntry, None]:
        """Runs the agent loop, yielding each trace entry the moment it happens.

        The console subscribes to this over SSE, so what the operator watches is
        the model's live decision log rather than a replay.
        """
        from google import genai
        from google.genai import types

        async with MCPToolRouter() as router:
            self._record(
                step_name="connect_mcp_servers",
                tool_type="system",
                action_summary=("Connected to MCP servers: " + ", ".join(router.server_names)),
                tool_name="mcp_initialize",
                tool_input={"servers": router.server_names, "transport": "stdio"},
                output_summary=(
                    f"{len(router.tools)} MCP tools available to the agent: "
                    + ", ".join(t.name for t in router.tools)
                ),
                duration_ms=0,
            )
            yield self.traces[-1]

            declarations = router.gemini_tool_declarations()
            tools = [
                types.Tool(
                    function_declarations=[types.FunctionDeclaration(**d) for d in declarations]
                )
            ]

            client = genai.Client()
            task = AGENT_TASK_PROMPT.format(
                incident_id=self.incident.incident_id,
                robot_id=self.incident.robot_telemetry.robot_id,
                scene=self.incident.stage_info.current_scene,
                take=self.incident.stage_info.current_take,
            )
            contents: list[types.Content] = [
                types.Content(role="user", parts=[types.Part(text=task)])
            ]

            config = types.GenerateContentConfig(
                system_instruction=INVESTIGATION_SYSTEM_PROMPT,
                tools=tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                thinking_config=types.ThinkingConfig(thinking_budget=2048),
            )

            for round_index in range(MAX_TOOL_ROUNDS):
                started = time.monotonic()
                response = await client.aio.models.generate_content(
                    model=settings.GEMINI_MODEL, contents=contents, config=config
                )
                think_ms = int((time.monotonic() - started) * 1000)

                calls = list(response.function_calls or [])
                if not calls:
                    self._record(
                        step_name="synthesize_diagnosis",
                        tool_type="gemini_reasoner",
                        action_summary=(
                            f"{settings.GEMINI_MODEL} finished tool use after "
                            f"{round_index} reasoning rounds and committed to a diagnosis"
                        ),
                        tool_name="gemini_generate_content",
                        tool_input={
                            "model": settings.GEMINI_MODEL,
                            "thinking_budget": 2048,
                            "rounds_used": round_index,
                        },
                        output_summary=_summarize(response.text or "(no text returned)"),
                        duration_ms=think_ms,
                    )
                    yield self.traces[-1]
                    self.verdict = await self._finalize(client, types, contents, response)
                    if self.traces:
                        yield self.traces[-1]
                    return

                candidate = response.candidates[0] if response.candidates else None
                if candidate and candidate.content:
                    contents.append(candidate.content)

                response_parts: list[types.Part] = []
                for call in calls:
                    args = dict(call.args or {})
                    call_started = time.monotonic()
                    result = await router.call(call.name, args)
                    payload, is_error = result.text, result.is_error
                    call_ms = int((time.monotonic() - call_started) * 1000)
                    server = router.server_of(call.name) or "unknown"
                    if result.images:
                        payload = (
                            f"{payload}\n[{len(result.images)} rendered frame(s) attached "
                            "below — look at them before concluding]"
                        )

                    self._record(
                        step_name=call.name,
                        tool_type=_trace_type(call.name),
                        action_summary=(f"Gemini chose {call.name} on the {server} MCP server"),
                        tool_name=f"mcp://{server}/{call.name}",
                        tool_input=args,
                        output_summary=_summarize(payload),
                        duration_ms=call_ms,
                        status="error" if is_error else "success",
                    )
                    yield self.traces[-1]
                    response_parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=call.name,
                                response={"result": _truncate(payload)},
                            )
                        )
                    )
                    # A rendered frame cannot ride inside a function response, so it
                    # is attached to the same turn as an inline image part. This is
                    # what lets the model actually look at the telemetry.
                    for blob, mime in result.images:
                        response_parts.append(types.Part.from_bytes(data=blob, mime_type=mime))
                contents.append(types.Content(role="user", parts=response_parts))

            logger.warning("Agent hit MAX_TOOL_ROUNDS without concluding")
            self._record(
                step_name="tool_budget_exhausted",
                tool_type="system",
                action_summary=(
                    f"Agent reached the {MAX_TOOL_ROUNDS}-round tool budget without "
                    "committing to a diagnosis"
                ),
                tool_name="agent_loop_guard",
                tool_input={"max_rounds": MAX_TOOL_ROUNDS},
                output_summary="No diagnosis produced; falling back to the recorded fixture.",
                duration_ms=0,
                status="warning",
            )
            yield self.traces[-1]
            self.verdict = None

    async def _finalize(
        self, client: Any, types: Any, contents: list[Any], last_response: Any
    ) -> AgentInvestigationOutput | None:
        """Asks for the diagnosis as strict JSON once tool use has finished."""
        if last_response.candidates and last_response.candidates[0].content:
            contents.append(last_response.candidates[0].content)
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=(
                            "Now emit the final investigation as JSON matching the "
                            "required schema. Use only findings from the tool results "
                            "above."
                        )
                    )
                ],
            )
        )
        started = time.monotonic()
        try:
            structured = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=INVESTIGATION_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=AgentInvestigationOutput,
                    thinking_config=types.ThinkingConfig(thinking_budget=1024),
                ),
            )
            parsed = AgentInvestigationOutput.model_validate(json.loads(structured.text))
        except Exception as e:  # noqa: BLE001 - a bad structured reply must not 500
            logger.warning("Structured diagnosis parse failed: %s", e)
            self._record(
                step_name="structured_output_failed",
                tool_type="gemini_reasoner",
                action_summary="Structured diagnosis could not be parsed",
                tool_name="gemini_structured_output",
                tool_input={"schema": "AgentInvestigationOutput"},
                output_summary=f"{type(e).__name__}: {e}"[:200],
                duration_ms=int((time.monotonic() - started) * 1000),
                status="error",
            )
            return None

        self._record(
            step_name="emit_structured_diagnosis",
            tool_type="gemini_reasoner",
            action_summary="Emitted the ranked diagnosis and recovery plan as strict JSON",
            tool_name="gemini_structured_output",
            tool_input={"schema": "AgentInvestigationOutput"},
            output_summary=_summarize(
                f"Primary: {parsed.primary_hypothesis.title} "
                f"({parsed.primary_hypothesis.confidence:.0%}); "
                f"{len(parsed.alternative_hypotheses)} alternatives, "
                f"{len(parsed.recommendations)} recovery actions."
            ),
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return parsed


__all__ = ["MCPGeminiAgent", "MCPUnavailableError"]
