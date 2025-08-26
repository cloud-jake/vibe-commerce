# Vibe Commerce - Vertex AI Search for retail Demo

Welcome to Vibe Commerce, a sample e-commerce web application built with Flask and Python. This project demonstrates how to integrate Google Cloud's **Vertex AI Search for retail** to power a modern, personalized shopping experience.

It showcases features like AI-driven product search, personalized recommendations, and real-time user event tracking.

## Features

- **AI-Powered Search**: Utilizes the Vertex AI Search API for fast and relevant product search.
- **Personalized Recommendations**: Displays a "Recommended For You" carousel on the homepage.
- **Product Detail Pages**: Dynamically generated pages for each product.
- **Shopping Cart**: A fully functional cart using Flask sessions.
- **Secure Server-Side Event Tracking**: Captures user events and forwards them to the Retail API via a secure backend endpoint, using service account credentials.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python (3.12 is recommended to ensure library compatibility)
- `pip` and `venv`
- Google Cloud SDK

You will also need a Google Cloud project with the **Retail API** enabled.

## Setup and Installation

Follow these steps to get the application running locally.

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd vibe-commerce
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    # On Windows, use: venv\Scripts\activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Authenticate with Google Cloud:**
    This command sets up your local machine with credentials to access Google Cloud APIs.
    ```bash
    gcloud auth application-default login
    ```

5.  **Configure Environment Variables:**
    For local development and deployment, create a file named `.env` in the project root. This file will hold your configuration and secrets. Add the following, replacing the values with your own:

    ```
    # .env

    # --- Google Cloud Project Configuration ---
    PROJECT_ID="your-gcp-project-id"
    REGION="us-central1"
    LOCATION="global"
    CATALOG_ID="default_catalog"
    SERVING_CONFIG_ID="your-serving-config-id"
    RECOMMENDATION_SERVING_CONFIG_ID="your-recommendation-config-id"

    # --- Google OAuth Configuration ---
    GOOGLE_CLIENT_ID="your-google-oauth-client-id.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET="your-google-oauth-client-secret"
    ```

    > **Note:** The `.gitignore` file is already configured to prevent the `.env` file from being committed to version control.

## Running the Application

### Locally
Once the setup is complete, you can start the Flask development server:

```bash
flask run
```

The application will be available at `http://127.0.0.1:5000`.

### Deployment
To deploy the application to Cloud Run, ensure your `.env` file is correctly populated and run the deployment script:

```bash
./deploy.sh
```

---

This project is intended for demonstration purposes to showcase the capabilities of Vertex AI Search for retail.