# Deploying the GECX Tools Middleware

This directory contains a lightweight Python service that translates CX Agent Studio requests into Google Cloud Retail API calls.

To expose these tools to your CX Agent Studio, you need to deploy this code to **Google Cloud Run** and then upload the `openapi.yaml` specification.

## Prerequisites
1. Ensure you have the `gcloud` CLI installed and authenticated.
2. Select the GCP project that hosts your Vibe Commerce resources:
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

## Step 1: Deploy to Cloud Run

Run the following command from this directory (`gecx_middleware/`) to package and deploy the API:

```bash
gcloud run deploy gecx-tools-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=YOUR_PROJECT_ID,LOCATION=global,CATALOG_ID=default_catalog"
```

*Note: Replace `YOUR_PROJECT_ID` with your actual Google Cloud Project ID. Ensure `LOCATION` and `CATALOG_ID` match what you use in `vibe-commerce/config.py`.*

When the deployment finishes, the terminal will print out a **Service URL** (e.g., `https://gecx-tools-api-xyz-uc.a.run.app`).

## Step 2: Update the OpenAPI Specification

1. Open `openapi.yaml` in this folder.
2. Find the line under `servers:` that says `url: https://YOUR_CLOUD_RUN_URL_HERE`.
3. Replace the placeholder URL with the actual **Service URL** generated in Step 1.

## Step 3: Import into CX Agent Studio

1. In the Google Cloud Console, open **CX Agent Studio**.
2. Navigate to your Root Agent (or the specific agent that holds the tools).
3. Under the **Tools** section, delete your old Python tool placeholders.
4. Click **Create Tool**.
5. Select **OpenAPI Tool**.
6. Give the tool a descriptive name (e.g., `VibeCommerceRetailAPI`).
7. **Upload** your modified `openapi.yaml` file.
8. Click **Save**.

Your GECX Agent is now directly integrated with your live Retail catalog via the OpenAPI schema! When users chat with the AI, the AI will evaluate their prompt, trigger operations like `searchProducts`, pass in the arguments, and stream the results back perfectly.
