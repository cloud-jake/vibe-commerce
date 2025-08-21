import os
import json
import traceback
import uuid
from flask import Flask, render_template, request, redirect, url_for, session
from google.api_core.exceptions import GoogleAPICallError
from google.cloud.retail_v2 import (
    PredictionServiceClient,
    ProductServiceClient,
    UserEventServiceClient,
    SearchServiceClient,
)
from google.cloud.retail_v2.types import (
    PredictRequest,
    Product,
    SearchResponse,
    WriteUserEventRequest,
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
search_placement = SearchServiceClient.serving_config_path(
    project=config.PROJECT_ID,
    location=config.LOCATION,
    catalog=config.CATALOG_ID,
    serving_config=config.SERVING_CONFIG_ID,
)

# Initialize the Search Service Client
search_client = SearchServiceClient()

# Initialize the Product Service Client
product_client = ProductServiceClient()

# Initialize the Prediction Service Client
prediction_client = PredictionServiceClient()

# Initialize the User Event Service Client
user_event_client = UserEventServiceClient()

@app.context_processor
def inject_shared_variables():
    """Injects variables needed in all templates for event tracking."""
    return dict(
        project_id=config.PROJECT_ID,
        catalog_id=config.CATALOG_ID,
        location=config.LOCATION,
        visitor_id=session.get('visitor_id')
    )


@app.before_request
def initialize_session():
    """Initialize the cart and visitor ID in the session if they don't exist."""
    if 'cart' not in session:
        session['cart'] = {} # Use a dictionary for faster lookups
        session['cart_total'] = 0.0
    if 'visitor_id' not in session:
        session['visitor_id'] = str(uuid.uuid4())


@app.route('/')
def index():
    """Homepage: Fetches and displays product recommendations."""
    recommendations = []
    error = None
    try:
        # The full resource name of the serving config
        recommendation_placement = (
            f"projects/{config.PROJECT_ID}/locations/{config.LOCATION}"
            f"/catalogs/{config.CATALOG_ID}/servingConfigs/{config.RECOMMENDATION_SERVING_CONFIG_ID}"
        )

        # Create a user event object
        user_event = UserEvent(
            event_type="home-page-view",
            visitor_id=session.get('visitor_id')
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
        print(f"Error getting recommendations: {e}\n{traceback.format_exc()}")

    return render_template('index.html', recommendations=recommendations, error=error, event_type='home-page-view')


@app.route('/search')
def search():
    """
    Performs a search using the Vertex AI Search for Commerce Retail API.
    """
    query = request.args.get('query', '').strip()
    # Add server-side validation to match the client-side minlength attribute
    if len(query) < 2:
        return redirect(url_for('index'))

    # Check for a URL parameter to control query expansion. Default to True.
    use_expansion = request.args.get('expand', 'true').lower() == 'true'

    # --- Build Search Request ---
    if use_expansion:
        # Enable query expansion to broaden the search for better results.
        # Pinning unexpanded results ensures that items matching the original
        # query are ranked higher.
        query_expansion_spec = SearchRequest.QueryExpansionSpec(
            condition=SearchRequest.QueryExpansionSpec.Condition.AUTO,
            pin_unexpanded_results=True
        )
    else:
        # Explicitly disable query expansion if the URL parameter is set to 'false'.
        query_expansion_spec = SearchRequest.QueryExpansionSpec(
            condition=SearchRequest.QueryExpansionSpec.Condition.DISABLED
        )

    search_request = SearchRequest(
        placement=search_placement,
        query=query,
        visitor_id=session.get('visitor_id'),  # A unique ID for the user session
        page_size=20,
        query_expansion_spec=query_expansion_spec,
    )

    # --- Call the Retail API ---
    try:
        search_response = search_client.search(search_request)
        # The search_response.results is a list of proto messages, not directly
        # JSON serializable. Convert them to dicts for the event tracker.
        results_for_js = [SearchResponse.SearchResult.to_dict(r) for r in search_response.results]
        return render_template(
            'search_results.html',
            results=search_response.results,
            results_json=results_for_js,
            query=query,
            use_expansion=use_expansion,
            event_type='search'
        )
    except Exception as e:
        print(f"Error during search: {e}\n{traceback.format_exc()}")
        return render_template('search_results.html', error=str(e), query=query, use_expansion=use_expansion, event_type='search')


@app.route('/product/<string:product_id>')
def product_detail(product_id):
    """
    Fetches and displays the details for a single product.
    """
    product_name = product_client.product_path(
        project=config.PROJECT_ID,
        location=config.LOCATION,
        catalog=config.CATALOG_ID,
        branch="0", # The default branch is '0'
        product=product_id
    )

    try:
        product_proto = product_client.get_product(name=product_name)
        # Convert the proto message to a dictionary for reliable JSON serialization
        product_dict = Product.to_dict(product_proto)
        return render_template(
            'product_detail.html',
            product=product_proto,
            product_json=product_dict,
            event_type='detail-page-view'
        )
    except Exception as e:
        print(f"Error fetching product details: {e}\n{traceback.format_exc()}")
        return render_template('product_detail.html', error=str(e))


@app.route('/api/track_event', methods=['POST'])
def track_event():
    """
    Receives a user event from the client and writes it to the Retail API.
    This provides a secure, server-side event ingestion mechanism.
    """
    event_data = request.get_json()
    if not event_data:
        return {"error": "Invalid JSON payload"}, 400

    try:
        # The parent catalog resource name
        parent = user_event_client.catalog_path(
            project=config.PROJECT_ID,
            location=config.LOCATION,
            catalog=config.CATALOG_ID
        )

        # Handle both a single event object and an array of events (from sendBeacon)
        events_to_process = event_data if isinstance(event_data, list) else [event_data]

        for event in events_to_process:
            # Construct the UserEvent object from the client-side payload
            user_event = UserEvent.from_json(json.dumps(event))

            # Write the event
            write_request = WriteUserEventRequest(parent=parent, user_event=user_event)
            user_event_client.write_user_event(request=write_request)

            print(f"Successfully wrote event: {user_event.event_type} for visitor {user_event.visitor_id}")

        return {"status": "success"}, 200
    except Exception as e:
        print(f"Error writing user event: {e}\n{traceback.format_exc()}")
        return {"error": "Failed to write event"}, 500


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Adds a product to the cart stored in the session."""
    product_id = request.form.get('product_id')
    product_title = request.form.get('product_title')
    price_str = request.form.get('product_price')
    try:
        # More robustly handle conversion from form string to float.
        product_price = float(price_str)
    except (ValueError, TypeError):
        # Default to 0.0 if price is missing, not a valid number, or None.
        product_price = 0.0
    product_image = request.form.get('product_image')

    if not product_id:
        return redirect(url_for('index'))

    # Add item to cart
    cart = session.get('cart', {})

    if product_id in cart:
        # Item exists, just increment quantity
        cart[product_id]['quantity'] += 1
    else:
        # Add new item to cart
        cart[product_id] = {
            'id': product_id,
            'title': product_title,
            'price': product_price,
            'image': product_image,
            'quantity': 1
        }
    session['cart'] = cart

    # Update total
    session['cart_total'] = sum(item['price'] * item['quantity'] for item in cart.values())

    # Redirect back to the page the user came from for a smoother experience
    return redirect(request.referrer or url_for('index'))


@app.route('/cart')
def view_cart():
    """Displays the shopping cart."""
    return render_template('cart.html', cart=session.get('cart', {}), total=session.get('cart_total', 0.0), event_type='shopping-cart-page-view')


@app.route('/remove_from_cart/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    """Removes an item from the cart."""
    cart = session.get('cart', {})
    # Safely remove the item if it exists
    cart.pop(product_id, None)
    session['cart'] = cart
    # Recalculate total
    session['cart_total'] = sum(item['price'] * item['quantity'] for item in cart.values())
    return redirect(url_for('view_cart'))


@app.route('/checkout', methods=['POST'])
def checkout():
    """Simulates checkout and redirects to a confirmation page."""
    cart_at_checkout = list(session.get('cart', {}).values())
    total_at_checkout = session.get('cart_total', 0.0)
    transaction_id = str(uuid.uuid4())

    # Store checkout details in session to pass to the confirmation page
    session['last_order'] = {
        'items': cart_at_checkout,
        'total': total_at_checkout,
        'transaction_id': transaction_id
    }

    # Clear the cart
    session['cart'] = {}
    session['cart_total'] = 0.0

    return redirect(url_for('purchase_confirmation'))


@app.route('/purchase_confirmation')
def purchase_confirmation():
    """Displays the purchase confirmation page and tracks the purchase event."""
    last_order = session.get('last_order')
    if not last_order:
        return redirect(url_for('index'))

    # Clear the last order from session after displaying it
    session.pop('last_order', None)
    return render_template('purchase_confirmation.html', order=last_order, event_type='purchase-complete')

if __name__ == '__main__':
    # This block is for running the app directly with `python app.py`
    # For production, use a WSGI server like Gunicorn.
    app.run(debug=True, port=5000)