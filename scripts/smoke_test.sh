#!/usr/bin/env bash
set -euo pipefail

TARGET_URL="${1:-http://localhost:8080}"
echo "=== Running CineOps Guardian Smoke Tests against ${TARGET_URL} ==="

# 1. Health Check
echo -n "[1/4] Checking /health endpoint... "
HEALTH=$(curl -fsSL "${TARGET_URL}/health")
echo "OK (${HEALTH})"

# 2. Status Check
echo -n "[2/4] Checking /api/v1/status endpoint... "
STATUS=$(curl -fsSL "${TARGET_URL}/api/v1/status")
echo "OK"

# 3. Active Incident
echo -n "[3/4] Checking active incident retrieval... "
INC_ID=$(curl -fsSL "${TARGET_URL}/api/v1/incidents/current" | python3 -c "import sys, json; print(json.load(sys.stdin).get('incident_id', ''))")
if [ "${INC_ID}" == "inc-stage-a-001" ]; then
  echo "OK (Incident: ${INC_ID})"
else
  echo "FAILED (Unexpected ID: ${INC_ID})"
  exit 1
fi

# 4. MCAP Recording Download
echo -n "[4/4] Checking MCAP recording download... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${TARGET_URL}/api/v1/incidents/inc-stage-a-001/recording.mcap")
if [ "${HTTP_CODE}" == "200" ]; then
  echo "OK (HTTP 200)"
else
  echo "FAILED (HTTP ${HTTP_CODE})"
  exit 1
fi

echo "=== All Smoke Tests PASSED Successfully ==="

