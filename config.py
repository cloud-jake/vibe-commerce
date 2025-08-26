# config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file for local development.
# In a containerized environment like Cloud Run, these will be set directly.
load_dotenv()

# --- Google Cloud Project Configuration ---
# Your Google Cloud project ID.
PROJECT_ID = os.environ.get("PROJECT_ID", "partarch-ecommerce-demo")

# The location of your Retail API resources (e.g., "global").
LOCATION = os.environ.get("LOCATION", "global")

# Your Catalog ID (e.g., "default_catalog").
CATALOG_ID = os.environ.get("CATALOG_ID", "default_catalog")

# Your Serving Config ID for search (e.g., "default_serving_config").
SERVING_CONFIG_ID = os.environ.get("SERVING_CONFIG_ID", "vibe-search-1")

# --- Recommendations Configuration ---
# Your Recommendation Serving Config ID (e.g., "recently_viewed_default").
RECOMMENDATION_SERVING_CONFIG_ID = os.environ.get("RECOMMENDATION_SERVING_CONFIG_ID", "recently_viewed_default")

# --- Google OAuth Configuration ---
# These are obtained from the Google Cloud Console when creating OAuth credentials.
# Store them in your .env file for local development.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
