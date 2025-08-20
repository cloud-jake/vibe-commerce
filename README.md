# Vibe Commerce - Vertex AI Search for retail Demo

Welcome to Vibe Commerce, a sample e-commerce web application built with Flask and Python. This project demonstrates how to integrate Google Cloud's **Vertex AI Search for retail** to power a modern, personalized shopping experience.

It showcases features like AI-driven product search, personalized recommendations, and real-time user event tracking.

## Features

- **AI-Powered Search**: Utilizes the Vertex AI Search API for fast and relevant product search.
- **Personalized Recommendations**: Displays a "Recommended For You" carousel on the homepage.
- **Product Detail Pages**: Dynamically generated pages for each product.
- **Shopping Cart**: A fully functional cart using Flask sessions.
- **Real-time Event Tracking**: Captures user events (`home-page-view`, `search`, `detail-page-view`, `add-to-cart`, `purchase-complete`) and sends them directly to the Retail API for model training and personalization.
- **Secure Configuration**: Uses environment variables to manage sensitive API keys, keeping them out of source control.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python (3.10 or newer)
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
    The application requires an API Key for real-time event tracking. This key should not be stored in source control.

    - Create a new file named `.env` in the root of the project.
    - Add your Retail API Key to this file.

    ```
    # .env
    RETAIL_API_KEY="your-api-key-here"
    ```
    > **Important**: The `.gitignore` file is already configured to ignore the `.env` file, ensuring your key is not accidentally committed to GitHub.

6.  **Update the Application Configuration:**
    Open `config.py` and update the following variables with your specific Google Cloud project details:
    - `PROJECT_ID`
    - `LOCATION`
    - `CATALOG_ID`
    - `SERVING_CONFIG_ID`
    - `RECOMMENDATION_SERVING_CONFIG_ID`

## Running the Application

Once the setup is complete, you can start the Flask development server:

```bash
flask run
```

The application will be available at `http://127.0.0.1:5000`.

---

This project is intended for demonstration purposes to showcase the capabilities of Vertex AI Search for retail.