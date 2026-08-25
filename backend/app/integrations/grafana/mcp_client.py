import logging
from typing import Any

import httpx

from backend.app.integrations.grafana.mock_client import MockGrafanaMCPClient
from backend.app.settings import settings

logger = logging.getLogger(__name__)


class GrafanaMCPClient:
    """Client for calling official Grafana MCP server (mcp-grafana) or fallback mock."""

    def __init__(self):
        self.mode = settings.DEMO_MODE
        self.mock_client = MockGrafanaMCPClient()
        self.base_url = settings.GRAFANA_URL
        self.token = settings.GRAFANA_SERVICE_ACCOUNT_TOKEN
        self.mcp_url = settings.GRAFANA_MCP_URL

    async def get_alert_rules(self, stage_id: str = "stage-a") -> list[dict[str, Any]]:
        if self.mode == "mock" or not self.token or self.token.startswith("glsa_placeholder"):
            return await self.mock_client.get_alert_rules(stage_id)

        # Real HTTP / MCP call
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {"Authorization": f"Bearer {self.token}"}
                resp = await client.get(
                    f"{self.base_url}/api/v1/provisioning/alert-rules", headers=headers
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"Grafana alert rule query failed, falling back to mock: {e}")
        return await self.mock_client.get_alert_rules(stage_id)

    async def query_prometheus(self, query: str, time_range: str = "5m") -> dict[str, Any]:
        if self.mode == "mock" or not self.token or self.token.startswith("glsa_placeholder"):
            return await self.mock_client.query_prometheus(query, time_range)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {"Authorization": f"Bearer {self.token}"}
                params = {"query": query}
                resp = await client.get(
                    f"{self.base_url}/api/datasources/proxy/uid/prometheus/api/v1/query",
                    headers=headers,
                    params=params,
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"Grafana Prometheus query failed: {e}")
        return await self.mock_client.query_prometheus(query, time_range)

    async def query_loki(self, logql: str, limit: int = 10) -> list[dict[str, Any]]:
        if self.mode == "mock" or not self.token or self.token.startswith("glsa_placeholder"):
            return await self.mock_client.query_loki(logql, limit)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {"Authorization": f"Bearer {self.token}"}
                params = {"query": logql, "limit": limit}
                resp = await client.get(
                    f"{self.base_url}/api/datasources/proxy/uid/loki/loki/api/v1/query_range",
                    headers=headers,
                    params=params,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for stream in data.get("data", {}).get("result", []):
                        labels = stream.get("stream", {})
                        for val in stream.get("values", []):
                            results.append({"timestamp": val[0], "labels": labels, "line": val[1]})
                    return results
        except Exception as e:
            logger.warning(f"Grafana Loki query failed: {e}")
        return await self.mock_client.query_loki(logql, limit)

    async def search_dashboards(self, query: str = "stage-a") -> list[dict[str, Any]]:
        if self.mode == "mock" or not self.token or self.token.startswith("glsa_placeholder"):
            return await self.mock_client.search_dashboards(query)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {"Authorization": f"Bearer {self.token}"}
                params = {"query": query}
                resp = await client.get(
                    f"{self.base_url}/api/search", headers=headers, params=params
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"Grafana search dashboards failed: {e}")
        return await self.mock_client.search_dashboards(query)
