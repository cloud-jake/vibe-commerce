#!/bin/bash
set -e

# This script deploys the application to Cloud Run.
# It sources environment variables from a .env file in the project root.

# Check if .env file exists and source it
if [ -f .env ]; then
  # Use set -a to export all variables from the sourced file
  set -a
  source .env
  set +a
else
  echo "Error: .env file not found. Please create it before deploying."
  exit 1
fi

# Set default values for variables if they are not defined in the .env file.
REGION=${REGION:-us-central1}
LOCATION=${LOCATION:-global}
CATALOG_ID=${CATALOG_ID:-default_catalog}
SERVING_CONFIG_ID=${SERVING_CONFIG_ID:-default_search}
RECOMMENDATION_SERVING_CONFIG_ID=${RECOMMENDATION_SERVING_CONFIG_ID:-recently_viewed_default}

# Validate that all required variables are set
REQUIRED_VARS=(
  "PROJECT_ID"
  "LOCATION"
  "CATALOG_ID"
  "SERVING_CONFIG_ID"
  "RECOMMENDATION_SERVING_CONFIG_ID"
  "GOOGLE_CLIENT_ID"
  "GOOGLE_CLIENT_SECRET"
)

for VAR_NAME in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!VAR_NAME}" ]; then
    echo "Error: Required environment variable '$VAR_NAME' is not set."
    echo "Please ensure it is defined in your .env file."
    exit 1
  fi
done

# Build and deploy to Cloud Run
gcloud run deploy vibe-commerce \
  --source . \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars="LOCATION=${LOCATION}" \
  --set-env-vars="CATALOG_ID=${CATALOG_ID}" \
  --set-env-vars="SERVING_CONFIG_ID=${SERVING_CONFIG_ID}" \
  --set-env-vars="RECOMMENDATION_SERVING_CONFIG_ID=${RECOMMENDATION_SERVING_CONFIG_ID}" \
  --set-env-vars="GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}" \
  --set-env-vars="GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}"

echo "Deployment to Cloud Run initiated successfully."
