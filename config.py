# config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file at the earliest possible point.
load_dotenv()

# --- Google Cloud Project Configuration ---
# Replace with your Google Cloud project ID
PROJECT_ID = "partarch-ecommerce-demo"

# Replace with the location of your Retail API resources (e.g., "global")
LOCATION = "global"

# Replace with your Catalog ID (e.g., "default_catalog")
CATALOG_ID = "default_catalog"

# Replace with your Serving Config ID (e.g., "default_serving_config")
# This is found under your Catalog in the Google Cloud Console.
SERVING_CONFIG_ID = "vibe-search-1"

# --- Recommendations Configuration ---
# Replace with your Recommendation Serving Config ID
# e.g., "recently_viewed_default"
RECOMMENDATION_SERVING_CONFIG_ID = "recently_viewed_default"

# --- Event Tracking Configuration ---
# Load the API Key from an environment variable for security.
API_KEY = os.getenv("RETAIL_API_KEY")

if not API_KEY:
    print("WARNING: RETAIL_API_KEY environment variable not set. Event tracking will not work.")
