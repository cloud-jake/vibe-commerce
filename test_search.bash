#!/bin/bash
set -e

# This script tests the search endpoint of the Retail API.
# It sources environment variables from a .env file in the project root.

# Check if .env file exists and source it
if [ -f .env ]; then
  # Use set -a to export all variables from the sourced file
  set -a
  source .env
  set +a
else
  echo "Error: .env file not found. Please create it before testing."
  exit 1
fi

# Validate that required variables are set
REQUIRED_VARS=(
  "PROJECT_ID"
  "LOCATION"
  "CATALOG_ID"
  "SERVING_CONFIG_ID"
)

for VAR_NAME in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!VAR_NAME}" ]; then
    echo "Error: Required environment variable '$VAR_NAME' is not set."
    echo "Please ensure it is defined in your .env file."
    exit 1
  fi
done

# Step 1: Get access token
export ACCESS_TOKEN=$(gcloud auth application-default print-access-token)

# Step 2: Define the API endpoint URL
export API_ENDPOINT="https://retail.googleapis.com/v2/projects/${PROJECT_ID}/locations/${LOCATION}/catalogs/${CATALOG_ID}/servingConfigs/${SERVING_CONFIG_ID}:search"

# Step 3: Run the curl command with the quota project header
# The new header is "-H 'X-Goog-User-Project: ${PROJECT_ID}'"
# Replace "weber" with a valid search term if needed.
curl -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}" \
  -d '{
    "query": "weber",
    "visitorId": "troubleshooting-visitor-id-123",
    "pageSize": 50
  }'
