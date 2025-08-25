# Step 1: Set environment variables (ensure PROJECT_ID is correct)
# This should be the Project ID where the Retail API is enabled.
export PROJECT_ID="partarch-ecommerce-demo"
export LOCATION="global"
export CATALOG_ID="default_catalog"
export SERVING_CONFIG_ID="vibe-search-1"
export ACCESS_TOKEN=$(gcloud auth application-default print-access-token)

# Step 2: Define the API endpoint URL
export API_ENDPOINT="https://retail.googleapis.com/v2/projects/${PROJECT_ID}/locations/${LOCATION}/catalogs/${CATALOG_ID}/servingConfigs/${SERVING_CONFIG_ID}:search"

# Step 3: Run the curl command with the quota project header
# The new header is "-H 'X-Goog-User-Project: ${PROJECT_ID}'"
# Replace "YOUR_SEARCH_QUERY" with a valid search term.
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

