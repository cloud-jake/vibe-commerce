import os
import json
from flask import Flask, render_template, request, redirect, url_for, session
from google.api_core.exceptions import GoogleAPICallError
from google.cloud.retail_v2 import (
    PredictionServiceClient,
    ProductServiceClient,
    SearchServiceClient,
)
from google.cloud.retail_v2.types import (
    PredictRequest,
    Product,
    SearchRequest,
    UserEvent,
)
from google.protobuf import struct_pb2

import config

app = Flask(__name__, template_folder="templates", static_folder="static")
# A secret key is needed for session management (e.g., for the cart)
app.secret_key = os.urandom(24)

# --- Vertex AI Search Client Initialization ---

# Placement for search results
search_placement = f"projects/{config.PROJECT_ID}/locations/{config.LOCATION}/catalogs/{config.CATALOG_ID}/servingConfigs/{config.SERVING_CONFIG_ID}"

# Initialize the Search Service Client
search_client = SearchServiceClient()

# Initialize the Product Service Client
product_client = ProductServiceClient()

# Initialize the Prediction Service Client
prediction_client = PredictionServiceClient()


@app.before_request
def initialize_cart():
    """Initialize the cart in the session if it doesn't exist."""
    if 'cart' not in session:
        session['cart'] = []
        session['cart_total'] = 0.0


@app.route('/')
def index():
    """Homepage: Fetches and displays product recommendations."""
    recommendations = []
    error = None
    try:
        # The full resource name of the serving config
        recommendation_placement = prediction_client.serving_config_path(
            project=app.config["PROJECT_ID"],
            location=app.config["LOCATION"],
            catalog=app.config["CATALOG_ID"],
            serving_config=app.config["RECOMMENDATION_SERVING_CONFIG_ID"],
        )

        # Create a user event object
        user_event = UserEvent(
            event_type="home-page-view",
            visitor_id="test-visitor-id"  # In a real app, manage this with cookies
        )

        # Create the predict request
        predict_request = PredictRequest(
            placement=recommendation_placement,
            user_event=user_event,
            page_size=10,
            params={"returnProduct": struct_pb2.Value(bool_value=True)}
        )

        # Get the prediction response
        response = prediction_client.predict(request=predict_request)

        # Process the results
        for result in response.results:
            if 'product' in result.metadata:
                product_struct = result.metadata['product']
                product_json = struct_pb2.Struct.to_json(product_struct)
                recommendations.append(Product.from_json(product_json))

    except (GoogleAPICallError, Exception) as e:
        error = str(e)
        print(f"Error getting recommendations: {e}")

    return render_template('index.html', recommendations=recommendations, error=error)


@app.route('/search')
def search():
    """
    Performs a search using the Vertex AI Search for Commerce Retail API.
    """
    query = request.args.get('query', '')
    if not query:
        return redirect(url_for('index'))

    # --- Build Search Request ---
    search_request = SearchRequest(
        placement=search_placement,
        query=query,
        visitor_id="test-visitor-id",  # A unique ID for the user session
        page_size=20
    )

    # --- Call the Retail API ---
    try:
        search_response = search_client.search(search_request)
        return render_template('search_results.html', results=search_response.results, query=query)
    except Exception as e:
        print(f"Error during search: {e}")
        return render_template('search_results.html', error=str(e), query=query)


@app.route('/product/<path:product_id>')
def product_detail(product_id):
    """
    Fetches and displays the details for a single product.
    """
    product_name = f"projects/{config.PROJECT_ID}/locations/{config.LOCATION}/catalogs/{config.CATALOG_ID}/branches/0/products/{product_id}"

    try:
        product = product_client.get_product(name=product_name)
        return render_template('product_detail.html', product=product)
    except Exception as e:
        print(f"Error fetching product details: {e}")
        return render_template('product_detail.html', error=str(e))


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Adds a product to the cart stored in the session."""
    product_id = request.form.get('product_id')
    product_title = request.form.get('product_title')
    price_str = request.form.get('product_price')
    product_price = float(price_str) if price_str else 0.0
    product_image = request.form.get('product_image')

    if not product_id:
        return redirect(url_for('index'))

    # Create a dictionary for the product
    cart_item = {
        'id': product_id,
        'title': product_title,
        'price': product_price,
        'image': product_image,
        'quantity': 1 # For simplicity, always add 1
    }

    # Add item to cart
    current_cart = session['cart']
    
    # Check if item is already in cart
    found = False
    for item in current_cart:
        if item['id'] == product_id:
            item['quantity'] += 1
            found = True
            break
    
    if not found:
        current_cart.append(cart_item)

    session['cart'] = current_cart

    # Update total
    session['cart_total'] = sum(item['price'] * item['quantity'] for item in session['cart'])

    return redirect(url_for('view_cart'))


@app.route('/cart')
def view_cart():
    """Displays the shopping cart."""
    return render_template('cart.html')


if __name__ == '__main__':
    # Ensure you have set up your Google Cloud credentials.
    # For local development, you can use: `gcloud auth application-default login`
    app.run(debug=True, port=8080)