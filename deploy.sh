#!/bin/bash
set -e

echo "Starting deployment at $(date)"

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
SITE_NAME=${SITE_NAME:-"Vibe Commerce"}
SITE_LOGO_URL=${SITE_LOGO_URL:-/static/logo.png}

# Set defaults for support search variables, mirroring config.py
SUPPORT_PROJECT_ID=${SUPPORT_PROJECT_ID:-$PROJECT_ID}
SUPPORT_LOCATION=${SUPPORT_LOCATION:-global}
SUPPORT_COLLECTION_ID=${SUPPORT_COLLECTION_ID:-default_collection}
SUPPORT_SERVING_CONFIG_ID=${SUPPORT_SERVING_CONFIG_ID:-default_search}

# Validate that all required variables are set
REQUIRED_VARS=(
  "PROJECT_ID"
  "LOCATION"
  "CATALOG_ID"
  "SERVING_CONFIG_ID"
  "RECOMMENDATION_SERVING_CONFIG_ID"
  "GOOGLE_CLIENT_ID"
  "GOOGLE_CLIENT_SECRET"
  "SECRET_KEY"
  "SUPPORT_ENGINE_ID"
)

for VAR_NAME in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!VAR_NAME}" ]; then
    echo "Error: Required environment variable '$VAR_NAME' is not set."
    echo "Please ensure it is defined in your .env file."
    exit 1
  fi
done

# Build and deploy to Cloud Run
# To make the command more robust and avoid issues with line breaks,
# we'll construct a single comma-separated string for all environment variables.
ENV_VARS="PROJECT_ID=${PROJECT_ID},"
ENV_VARS+="LOCATION=${LOCATION},"
ENV_VARS+="CATALOG_ID=${CATALOG_ID},"
ENV_VARS+="SERVING_CONFIG_ID=${SERVING_CONFIG_ID},"
ENV_VARS+="RECOMMENDATION_SERVING_CONFIG_ID=${RECOMMENDATION_SERVING_CONFIG_ID},"
ENV_VARS+="GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID},"
ENV_VARS+="GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET},"
ENV_VARS+="SECRET_KEY=${SECRET_KEY},"
ENV_VARS+="SITE_NAME=${SITE_NAME},"
ENV_VARS+="SITE_LOGO_URL=${SITE_LOGO_URL},"
ENV_VARS+="SUPPORT_PROJECT_ID=${SUPPORT_PROJECT_ID},"
ENV_VARS+="SUPPORT_LOCATION=${SUPPORT_LOCATION},"
ENV_VARS+="SUPPORT_COLLECTION_ID=${SUPPORT_COLLECTION_ID},"
ENV_VARS+="SUPPORT_ENGINE_ID=${SUPPORT_ENGINE_ID},"
ENV_VARS+="SUPPORT_SERVING_CONFIG_ID=${SUPPORT_SERVING_CONFIG_ID}"

gcloud run deploy vibe-commerce \
  --source . \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS"

echo "Deployment to Cloud Run initiated successfully."
