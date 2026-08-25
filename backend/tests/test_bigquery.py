import pytest

from backend.app.integrations.bigquery.client import BigQueryHistoricalClient


@pytest.mark.asyncio
async def test_bigquery_search():
    client = BigQueryHistoricalClient()
    matches = await client.search_similar_incidents(symptoms=["tf_drift", "lens_swap"])
    assert len(matches) >= 1
    assert matches[0].similarity_score > 0.8
