# Set your project ID and region
export PROJECT_ID="partarch-ecommerce-demo"
export REGION="us-central1"

# Build and deploy to Cloud Run
gcloud run deploy vibe-commerce \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=$PROJECT_ID" \
  --set-env-vars="LOCATION=global" \
  --set-env-vars="CATALOG_ID=default_catalog" \
  --set-env-vars="SERVING_CONFIG_ID=vibe-search-1" \
  --set-env-vars="RECOMMENDATION_SERVING_CONFIG_ID=recently_viewed_default"
