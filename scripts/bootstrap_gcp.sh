#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-project-55fbcfd2-0ad6-4c99-a25}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
DATASET="${BIGQUERY_DATASET:-cineops_guardian}"
BUCKET="${GCS_BUCKET:-cineops-guardian-evidence}"

echo "=== Bootstrapping CineOps Guardian on GCP ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region:     ${REGION}"
echo "BigQuery:   ${DATASET}"
echo "GCS Bucket: ${BUCKET}"

# Enable required Google APIs
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  --project="${PROJECT_ID}" || true

echo "=== GCP Bootstrap Configuration Complete ==="

