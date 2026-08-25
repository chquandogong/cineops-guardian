import logging

from backend.app.domain.mock_data import get_mock_incident
from backend.app.domain.models import HistoricalIncidentMatch
from backend.app.settings import settings

logger = logging.getLogger(__name__)


class BigQueryHistoricalClient:
    """Client for querying synthetic historical incident records in BigQuery."""

    def __init__(self):
        self.project_id = settings.GOOGLE_CLOUD_PROJECT
        self.dataset_id = settings.BIGQUERY_DATASET
        self.mode = settings.DEMO_MODE

    async def search_similar_incidents(
        self, symptoms: list[str], asset_type: str = "camera_dolly", limit: int = 3
    ) -> list[HistoricalIncidentMatch]:
        if self.mode == "mock":
            return get_mock_incident().historical_matches

        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=self.project_id)
            query = f"""
                SELECT
                    incident_id,
                    event_date as date,
                    stage_name as stage,
                    asset_id,
                    scene_take,
                    symptoms_summary as symptoms,
                    confirmed_root_cause,
                    recovery_action as action_taken,
                    delay_minutes,
                    similarity_score
                FROM `{self.project_id}.{self.dataset_id}.incident_history`
                WHERE asset_type = @asset_type
                ORDER BY similarity_score DESC
                LIMIT @limit
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("asset_type", "STRING", asset_type),
                    bigquery.ScalarQueryParameter("limit", "INT64", limit),
                ],
                maximum_bytes_billed=50_000_000,
            )
            query_job = client.query(query, job_config=job_config)
            results = []
            for row in query_job:
                results.append(HistoricalIncidentMatch(**dict(row.items())))
            return results if results else get_mock_incident().historical_matches
        except Exception as e:
            logger.warning(f"BigQuery query failed, falling back to deterministic fixture: {e}")
            return get_mock_incident().historical_matches
