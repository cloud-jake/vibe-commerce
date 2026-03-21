import os
import json
from flask import Flask, request, jsonify
from google.cloud import retail_v2

app = Flask(__name__)

# Load config from environment variables (Cloud Run sets these)
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION", "global")
CATALOG_ID = os.environ.get("CATALOG_ID", "default_catalog")
SEARCH_SERVING_CONFIG_ID = os.environ.get("SEARCH_SERVING_CONFIG_ID", "default_search")
BRANCH_NAME = os.environ.get("BRANCH_NAME", "default_branch")

# Initialize Retail API clients (these will automatically authenticate in Cloud Run)
search_client = retail_v2.SearchServiceClient()
product_client = retail_v2.ProductServiceClient()

@app.route("/search_products", methods=["GET"])
def search_products():
    """
    Searches the Vertex AI Search for Commerce catalog and returns simplified product cards.
    """
    query = request.args.get("query", "")
    category = request.args.get("category", "")
    
    if not PROJECT_ID:
        return jsonify({"error": "PROJECT_ID environment variable not set on server"}), 500

    placement = f"projects/{PROJECT_ID}/locations/{LOCATION}/catalogs/{CATALOG_ID}/servingConfigs/{SEARCH_SERVING_CONFIG_ID}"
    
    # Configure the search request
    search_request = retail_v2.SearchRequest(
        placement=placement,
        query=query,
        visitor_id="gecx-agent-integration", # Standardized ID for the agent
        page_size=5  # Top 5 to avoid overwhelming the LLM prompt context
    )
    
    if category:
        search_request.filter = f'categories: ANY("{category}")'

    try:
        response = search_client.search(search_request)
        results = []
        for result in response.results:
            product = result.product
            # Return only the essential fields the LLM needs to format an answer
            results.append({
                "id": product.id,
                "title": product.title,
                "price": product.price_info.price if product.price_info else None,
                "uri": product.uri,
                "description": product.description[:300] + "..." if product.description and len(product.description) > 300 else product.description
            })
            
        return jsonify({"products": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_product_details", methods=["GET"])
def get_product_details():
    """
    Retrieves the full dataset for a specific product by ID.
    """
    product_id = request.args.get("product_id")
    if not product_id:
        return jsonify({"error": "product_id is required"}), 400
        
    name = f"projects/{PROJECT_ID}/locations/{LOCATION}/catalogs/{CATALOG_ID}/branches/{BRANCH_NAME}/products/{product_id}"
    
    try:
        product = product_client.get_product(name=name)
        return jsonify({
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "price": product.price_info.price if product.price_info else None,
            "availability": product.availability.name if product.availability else "UNKNOWN",
            "categories": list(product.categories),
            "uri": product.uri
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_support_info", methods=["GET"])
def get_support_info():
    """
    Returns general store policies and contact links for the agent to reference.
    """
    topic = request.args.get("topic", "").lower()
    
    info = {
        "returns": "Items can be returned within 30 days of purchase with a receipt. Return shipping is free.",
        "shipping": "Standard shipping takes 3-5 business days. Expedited shipping is available at checkout.",
        "contact": "You can reach support at support@vibe-commerce.com or call 1-800-555-0199."
    }
    
    # Return a specific topic if requested, otherwise return all
    if topic in info:
        return jsonify({topic: info[topic]})
    return jsonify(info)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
