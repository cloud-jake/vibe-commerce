#!/bin/bash
set -e

# This script tests the recommendations endpoint of the Retail API.
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
  "RECOMMENDATION_SERVING_CONFIG_ID"
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
export API_ENDPOINT="https://retail.googleapis.com/v2/projects/${PROJECT_ID}/locations/${LOCATION}/catalogs/${CATALOG_ID}/servingConfigs/${RECOMMENDATION_SERVING_CONFIG_ID}:predict"

# Step 3: Run the curl command
# This command simulates a 'home-page-view' event to get recommendations.
# The "returnProduct": true parameter is crucial to get full product details
# back in the response, which is what the application does.
curl -X POST \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}" \
  -d '{
    "userEvent": {
      "eventType": "home-page-view",
      "visitorId": "troubleshooting-visitor-id-123"
    },
    "params": {
      "returnProduct": true
    },
    "pageSize": 10
  }'