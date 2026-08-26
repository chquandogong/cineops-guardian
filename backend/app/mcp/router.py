"""MCP client router.

Opens stdio sessions to every Model Context Protocol server the agent is allowed
to use, aggregates their tool catalogues, exposes them to Gemini as function
declarations, and dispatches Gemini's chosen calls back over MCP.

Two servers are wired today:

* ``grafana``  — the official ``grafana/mcp-grafana`` binary, giving the agent
  Prometheus and Loki access through Grafana Cloud.
* ``cineops``  — this project's own server (``backend/mcp_servers/cineops_mcp.py``),
  covering Foxglove, BigQuery, GCS and the ROS2 MCAP inspector.

Every tool the agent invokes therefore travels over MCP; nothing calls a vendor
REST API directly from the agent loop.
"""

import base64
import logging
import os
import shutil
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from backend.app.settings import settings

logger = logging.getLogger(__name__)

# The Grafana MCP server ships 70+ tools. Exposing all of them to the model
# bloats the prompt and invites irrelevant calls, so the agent gets the
# observability subset this incident class actually needs.
GRAFANA_TOOL_ALLOWLIST = {
    "list_datasources",
    "query_prometheus",
    "query_loki_logs",
    "list_prometheus_metric_names",
    "list_loki_label_names",
}


@dataclass
class MCPTool:
    """A tool discovered on an MCP server, addressed by its server."""

    server: str
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPCallResult:
    """What a tool returned: its text, any rendered frames, and whether it failed."""

    text: str
    images: list[tuple[bytes, str]] = field(default_factory=list)
    is_error: bool = False


class MCPUnavailableError(RuntimeError):
    """Raised when no MCP server could be reached, so the agent must not pretend."""


def _grafana_server_params() -> StdioServerParameters | None:
    binary = settings.MCP_GRAFANA_BINARY or shutil.which("mcp-grafana")
    if not binary or not os.path.exists(binary):
        logger.warning("mcp-grafana binary not found at %r; skipping Grafana MCP", binary)
        return None
    token = settings.GRAFANA_SERVICE_ACCOUNT_TOKEN
    if not token or token.startswith("glsa_placeholder"):
        logger.warning("Grafana service account token not configured; skipping Grafana MCP")
        return None
    return StdioServerParameters(
        command=binary,
        args=["-t", "stdio"],
        env={
            **os.environ,
            "GRAFANA_URL": settings.GRAFANA_URL,
            "GRAFANA_SERVICE_ACCOUNT_TOKEN": token,
        },
    )


def _cineops_server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.mcp_servers.cineops_mcp"],
        env={**os.environ},
    )


class MCPToolRouter:
    """Async context manager holding live MCP sessions for one investigation."""

    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self._sessions: dict[str, ClientSession] = {}
        self.tools: list[MCPTool] = []

    async def __aenter__(self) -> "MCPToolRouter":
        wanted: list[tuple[str, StdioServerParameters | None]] = [
            ("grafana", _grafana_server_params()),
            ("cineops", _cineops_server_params()),
        ]
        for server_name, params in wanted:
            if params is None:
                continue
            try:
                streams = await self._stack.enter_async_context(stdio_client(params))
                session = await self._stack.enter_async_context(
                    ClientSession(streams[0], streams[1])
                )
                await session.initialize()
                listed = await session.list_tools()
            except Exception as e:  # noqa: BLE001 - one bad server must not kill the rest
                logger.warning("MCP server %r unavailable: %s", server_name, e)
                continue

            self._sessions[server_name] = session
            for tool in listed.tools:
                if server_name == "grafana" and tool.name not in GRAFANA_TOOL_ALLOWLIST:
                    continue
                self.tools.append(
                    MCPTool(
                        server=server_name,
                        name=tool.name,
                        description=(tool.description or "").strip(),
                        input_schema=_tool_schema(tool),
                    )
                )
            logger.info("MCP server %r connected", server_name)

        if not self._sessions:
            await self._stack.aclose()
            raise MCPUnavailableError("no MCP server could be reached")
        return self

    async def __aexit__(self, *exc: object) -> None:
        try:
            await self._stack.aclose()
        except Exception as e:  # noqa: BLE001 - transport teardown noise is not a failure
            logger.debug("MCP session teardown raised during close: %s", e)

    # ------------------------------------------------------------------ #
    @property
    def server_names(self) -> list[str]:
        return sorted(self._sessions)

    def server_of(self, tool_name: str) -> str | None:
        for tool in self.tools:
            if tool.name == tool_name:
                return tool.server
        return None

    def gemini_tool_declarations(self) -> list[dict[str, Any]]:
        """MCP tool catalogue as Gemini function declarations."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters_json_schema": _sanitize_schema(tool.input_schema),
            }
            for tool in self.tools
        ]

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> MCPCallResult:
        """Invokes an MCP tool and returns its text, any images, and error state."""
        server_name = self.server_of(tool_name)
        if server_name is None:
            return MCPCallResult(text=f"unknown tool {tool_name!r}", is_error=True)
        session = self._sessions[server_name]
        try:
            result = await session.call_tool(tool_name, arguments or {})
        except Exception as e:  # noqa: BLE001 - surface tool failure to the model
            logger.warning("MCP call %s.%s failed: %s", server_name, tool_name, e)
            return MCPCallResult(text=f"tool call failed: {e}", is_error=True)

        chunks: list[str] = []
        images: list[tuple[bytes, str]] = []
        for content in result.content:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
                continue
            # MCP image content arrives base64-encoded; hand the raw bytes on so the
            # agent can attach them to the model conversation.
            raw = getattr(content, "data", None)
            mime = getattr(content, "mime_type", None) or getattr(content, "mimeType", None)
            if raw and mime and str(mime).startswith("image/"):
                try:
                    images.append((base64.b64decode(raw), str(mime)))
                except Exception as e:  # noqa: BLE001 - a bad image is not fatal
                    logger.warning("MCP image decode failed for %s: %s", tool_name, e)
        payload = "\n".join(chunks)
        if not payload:
            payload = (
                f"({len(images)} image(s) returned; see the attached frame)"
                if images
                else "(no textual content returned)"
            )
        # MCP SDKs have used both spellings; a tool that raised also comes back as
        # an "Error executing tool ..." payload, which the model must see as failed
        # so it can correct its arguments and retry.
        flagged = bool(getattr(result, "is_error", False) or getattr(result, "isError", False))
        looks_failed = payload.startswith("Error executing tool") or (
            "returned status code 4" in payload or "returned status code 5" in payload
        )
        return MCPCallResult(text=payload, images=images, is_error=flagged or looks_failed)


def _tool_schema(tool: Any) -> dict[str, Any]:
    """Reads a tool's JSON Schema across MCP SDK naming conventions."""
    raw = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None)
    if isinstance(raw, dict) and raw:
        return raw
    return {"type": "object", "properties": {}}


def _sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Strips JSON Schema keywords the Gemini function-calling parser rejects."""
    drop = {"$schema", "$defs", "definitions", "additionalProperties", "title"}

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items() if k not in drop}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    cleaned = walk(schema)
    if not isinstance(cleaned, dict) or "type" not in cleaned:
        return {"type": "object", "properties": {}}
    cleaned.setdefault("properties", {})
    return cleaned
