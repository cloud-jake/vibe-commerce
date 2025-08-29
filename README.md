# Vibe Commerce - A Vertex AI Search for Commerce Demo

Vibe Commerce is a fictional e-commerce site built to demonstrate the powerful capabilities of **[Google Cloud's Vertex AI Search for Commerce](https://cloud.google.com/solutions/vertex-ai-search-commerce)**. It's designed to illustrate how AI can create a modern, personalized, and intelligent shopping experience from the ground up.

This entire demo site was developed by a single developer with the assistance of **[Gemini Code Assist](https://codeassist.google/)**.

## Key Features

This demo highlights several core features of Vertex AI Search for Commerce:

*   **Site Search:** Experience fast, relevant, and intuitive search results that understand user intent, not just keywords. Includes rich features like faceting and query expansion.
*   **Product Recommendations:** Discover products tailored to your browsing history and preferences with "Recommended For You" carousels on the homepage.
*   **Conversational Commerce:** Engage with our AI-powered chat assistant, built on the Conversational Search API. This feature understands natural language queries, maintains conversational context, and provides helpful, AI-generated responses. It then uses the context of the conversation to fetch relevant product results, guiding users through their shopping journey.

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.8+
*   `pip` and `venv`
*   Google Cloud SDK installed and initialized.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/cloud-jake/vibe-commerce.git
    cd vibe-commerce
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows, use: venv\Scripts\activate
    ```

3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure your environment:**
    Create a `.env` file in the root of the project and add the necessary environment variables for your Google Cloud project, including `PROJECT_ID`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and a `SECRET_KEY`.

5.  **Authenticate with Google Cloud:**
    Log in with your user credentials for application-default authentication.
    ```bash
    gcloud auth application-default login
    ```

### Running the Application

Once the installation and configuration are complete, you can run the Flask development server:
```bash
flask run
```
The application will be available at `http://127.0.0.1:5000`.

## Inspiration

The design and spirit of this demo site are affectionately modeled after [Toys "R" Us](https://en.wikipedia.org/wiki/Toys_%22R%22_Us), a beloved childhood toy store that was a cultural icon in the 1980s. This project aims to recapture a small piece of that nostalgic experience within a modern, AI-powered e-commerce framework.

## Author

This project was created by **Jake Holmquist**, Field CTO, Google Cloud at Valtech.

The complete source code for this project is available on GitHub: [https://github.com/cloud-jake/vibe-commerce](https://github.com/cloud-jake/vibe-commerce).