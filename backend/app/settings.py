from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App & Environment
    PROJECT_NAME: str = "CineOps Guardian"
    VERSION: str = "2.1.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    DEMO_MODE: Literal["mock", "real"] = "mock"
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # Google Cloud
    GOOGLE_CLOUD_PROJECT: str = "project-55fbcfd2-0ad6-4c99-a25"
    GOOGLE_CLOUD_LOCATION: str = "global"
    GEMINI_MODEL: str = "gemini-3.7-flash"
    GEMINI_THINKING_LEVEL: str = "HIGH"
    BIGQUERY_DATASET: str = "cineops_guardian"
    GCS_BUCKET: str = "cineops-guardian-evidence"

    # Grafana & MCP
    GRAFANA_URL: str = "https://your-stack.grafana.net"
    GRAFANA_SERVICE_ACCOUNT_TOKEN: str = "glsa_placeholder"
    GRAFANA_MCP_URL: str = "http://localhost:8000"
    GRAFANA_STACK_ID: str = "123456"
    # Datasource UIDs used by the Grafana datasource proxy. Grafana Cloud stacks
    # provision these as `grafanacloud-prom` / `grafanacloud-logs`; self-hosted
    # Grafana commonly uses `prometheus` / `loki`.
    GRAFANA_PROM_DS_UID: str = "grafanacloud-prom"
    GRAFANA_LOKI_DS_UID: str = "grafanacloud-logs"
    # Loki query_range lookback. Defaults past the 1h Loki default so stage
    # telemetry recorded earlier in a shoot day is still returned.
    GRAFANA_LOKI_LOOKBACK_DAYS: int = 7
    GRAFANA_OTLP_ENDPOINT: str = "https://otlp-gateway-prod-us-east-0.grafana.net/otlp"
    GRAFANA_OTLP_USERNAME: str = "123456"
    GRAFANA_OTLP_TOKEN: str = "glc_placeholder"

    # Foxglove Data Platform
    FOXGLOVE_API_KEY: str = "fox_sk_placeholder"
    FOXGLOVE_ORG_SLUG: str = "your-org"
    # Layout the operator link opens with. Without it Foxglove uses the default
    # layout, whose panels have no topics enabled — the recording loads and shows
    # nothing, which is what this project shipped before.
    FOXGLOVE_LAYOUT_ID: str = ""

    # Model Context Protocol
    # Path to the official grafana/mcp-grafana binary, spawned over stdio. The
    # container installs it at /usr/local/bin/mcp-grafana.
    MCP_GRAFANA_BINARY: str = "/usr/local/bin/mcp-grafana"

    # Known-good baseline take used by the comparison tool. BASELINE_TF_Z is the
    # TF Z-translation the reference rig settles on; setting it to the incident's
    # value is how the comparison is ablation-tested — if the agent still blames
    # TF drift when the baseline shows the same value, the tool is decorative.
    BASELINE_TF_Z: float = 0.350

    # Stage Metadata
    DEFAULT_STAGE_ID: str = "stage-a-virtual-prod"
    DEFAULT_ROBOT_ID: str = "dolly-alpha-01"


settings = Settings()
