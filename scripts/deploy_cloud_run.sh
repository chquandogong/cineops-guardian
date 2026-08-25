#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-project-55fbcfd2-0ad6-4c99-a25}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="cineops-guardian"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "=== Deploying CineOps Guardian to Cloud Run ==="
echo "Target: ${SERVICE_NAME} in ${REGION} (Project: ${PROJECT_ID})"

# Build container with Google Cloud Build
gcloud builds submit --tag "${IMAGE_NAME}" --project="${PROJECT_ID}"

# Deploy to Cloud Run
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE_NAME}" \
  --platform=managed \
  --region="${REGION}" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=2 \
  --set-env-vars="DEMO_MODE=mock,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GEMINI_MODEL=gemini-3.7-flash" \
  --project="${PROJECT_ID}"

echo "=== Deployment Complete ==="

