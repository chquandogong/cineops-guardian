import logging
import os

from backend.app.settings import settings

logger = logging.getLogger(__name__)


class GCSClient:
    """Client for uploading and generating signed URLs for MCAP evidence recordings in GCS."""

    def __init__(self):
        self.bucket_name = settings.GCS_BUCKET
        self.mode = settings.DEMO_MODE

    async def upload_recording(self, local_path: str, destination_blob: str) -> str:
        if self.mode == "mock" or not os.path.exists(local_path):
            return "/api/v1/incidents/inc-stage-a-001/recording.mcap"

        try:
            from google.cloud import storage

            client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT)
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(destination_blob)
            blob.upload_from_filename(local_path)
            return f"https://storage.googleapis.com/{self.bucket_name}/{destination_blob}"
        except Exception as e:
            logger.warning(f"GCS upload failed, using local endpoint link: {e}")
            return "/api/v1/incidents/inc-stage-a-001/recording.mcap"
