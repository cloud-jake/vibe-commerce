# config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file for local development.
# In a containerized environment like Cloud Run, these will be set directly.
load_dotenv()

# --- Google Cloud Project Configuration ---
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION")
CATALOG_ID = os.environ.get("CATALOG_ID")
SERVING_CONFIG_ID = os.environ.get("SERVING_CONFIG_ID")

# --- GECX Agent Configuration ---
GECX_AGENT_ID = os.environ.get("GECX_AGENT_ID")
GECX_LOCATION = os.environ.get("GECX_LOCATION", "global")


# --- Recommendations Configuration ---
RECOMMENDATION_SERVING_CONFIG_ID = os.environ.get("RECOMMENDATION_SERVING_CONFIG_ID")

# --- Flask Session Configuration ---
# A secret key for signing the session cookie. This should be a long, random
# string. In production, this MUST be set as an environment variable.
SECRET_KEY = os.environ.get("SECRET_KEY")

# --- Google OAuth Configuration ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

# --- Support Agent Feature Flag ---
ENABLE_SUPPORT_AGENT = os.environ.get("ENABLE_SUPPORT_AGENT", "true").lower() == "true"

# --- Support Search Configuration ---
# These are for the separate Discovery Engine datastore for support content.
SUPPORT_PROJECT_ID = os.environ.get("SUPPORT_PROJECT_ID", PROJECT_ID)
SUPPORT_LOCATION = os.environ.get("SUPPORT_LOCATION", "global")
SUPPORT_COLLECTION_ID = os.environ.get("SUPPORT_COLLECTION_ID", "default_collection")
SUPPORT_ENGINE_ID = os.environ.get("SUPPORT_ENGINE_ID")
SUPPORT_SERVING_CONFIG_ID = os.environ.get("SUPPORT_SERVING_CONFIG_ID", "default_search")

# --- Support Intent URLs (Optional) ---
# These URLs are used by the conversational agent to direct users to the
# correct support pages when a relevant intent is detected. They default to
# internal routes if not explicitly set in the environment.
SUPPORT_INTENT_URLS = {
    "ORDER_SUPPORT": os.environ.get("SUPPORT_URL_ORDER_SUPPORT"),
    "DEALS_AND_COUPONS": os.environ.get("SUPPORT_URL_DEALS_AND_COUPONS"),
    "STORE_RELEVANT": os.environ.get("SUPPORT_URL_STORE_RELEVANT"),
    "RETAIL_SUPPORT": os.environ.get("SUPPORT_URL_RETAIL_SUPPORT"),
}

# --- Site Branding Configuration (Optional) ---
SITE_NAME = os.environ.get("SITE_NAME", "Vibe Commerce")
SITE_LOGO_URL = os.environ.get("SITE_LOGO_URL", "/static/logo.png")

# --- Validate that all required environment variables are set ---
# This ensures the application fails fast if configuration is missing.
REQUIRED_CONFIG = {
    "PROJECT_ID": PROJECT_ID,
    "LOCATION": LOCATION,
    "CATALOG_ID": CATALOG_ID,
    "SERVING_CONFIG_ID": SERVING_CONFIG_ID,
    "RECOMMENDATION_SERVING_CONFIG_ID": RECOMMENDATION_SERVING_CONFIG_ID,
    "SECRET_KEY": SECRET_KEY,
    "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
}

# Conditionally require SUPPORT_ENGINE_ID only if the feature is enabled.
if ENABLE_SUPPORT_AGENT:
    REQUIRED_CONFIG["SUPPORT_ENGINE_ID"] = SUPPORT_ENGINE_ID

missing_vars = [key for key, value in REQUIRED_CONFIG.items() if not value]
if missing_vars:
    raise ValueError(
        f"Missing required environment variables: {', '.join(missing_vars)}. "
        "Please set them in your .env file for local development."
    )
