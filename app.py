import os
import json
import math
import traceback
import uuid
from authlib.integrations.flask_client import OAuth
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from google.api_core.exceptions import GoogleAPICallError
from google.cloud.retail_v2alpha import ConversationalSearchServiceClient
from google.cloud.retail_v2alpha.types import ConversationalSearchRequest, ConversationalSearchResponse
from google.cloud.retail_v2 import (
    PredictionServiceClient,
    ProductServiceClient,
    UserEventServiceClient,
    SearchServiceClient,
    CompletionServiceClient,
)
from google.cloud.retail_v2.types import (
    CompleteQueryRequest,
    PredictRequest,
    PredictResponse,
    Product,
    SearchResponse,
    WriteUserEventRequest,
    SearchRequest,
    UserEvent,
)
from google.protobuf import json_format
from google.protobuf import struct_pb2
from werkzeug.middleware.proxy_fix import ProxyFix

import config

app = Flask(__name__, template_folder="templates", static_folder="static")

# Enable the 'do' extension for Jinja2 templates. This is required for the
# complex category hierarchy processing in `categories.html`.
app.jinja_env.add_extension('jinja2.ext.do')

# When deploying to a managed service like Cloud Run, the app is behind a
# reverse proxy. The ProxyFix middleware helps the app correctly handle
# headers like X-Forwarded-For and X-Forwarded-Proto, which is crucial for
# generating correct external URLs (e.g., for OAuth callbacks).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# A stable secret key is needed for session management. It's loaded from config
# and must be set in the environment for the app to run.
# The check for its existence is now handled centrally in config.py.
app.secret_key = config.SECRET_KEY

# --- OAuth Client Initialization ---
oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=config.GOOGLE_CLIENT_ID,
    client_secret=config.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


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

# Initialize the Completion Service Client for autocomplete
completion_client = CompletionServiceClient()

# Initialize the Product Service Client
product_client = ProductServiceClient()

# Initialize the Prediction Service Client
prediction_client = PredictionServiceClient()

# Initialize the User Event Service Client
user_event_client = UserEventServiceClient()

# Initialize the Conversational Search Service Client from v2alpha
conversational_search_client = ConversationalSearchServiceClient()

# Placement for conversational search, using 'default_search' as per the guide
conversational_placement = (
    f"projects/{config.PROJECT_ID}/locations/{config.LOCATION}/catalogs/"
    f"{config.CATALOG_ID}/placements/default_search"
)


@app.context_processor
def inject_shared_variables():
    """Injects variables needed in all templates."""
    return dict(
        project_id=config.PROJECT_ID,
        catalog_id=config.CATALOG_ID,
        location=config.LOCATION,
        visitor_id=session.get('visitor_id'),
        user=session.get('user'),
        site_name=config.SITE_NAME,
        site_logo_url=config.SITE_LOGO_URL,
    )


@app.before_request
def initialize_session():
    """Initialize the cart and visitor ID in the session if they don't exist."""
    if 'cart' not in session:
        session['cart'] = {} # Use a dictionary for faster lookups
        session['cart_total'] = 0.0
    if 'visitor_id' not in session:
        session['visitor_id'] = str(uuid.uuid4())


@app.route('/login')
def login():
    """Redirects to Google's authentication page."""
    redirect_uri = url_for('callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/callback')
def callback():
    """Handles the callback from Google after authentication."""
    try:
        token = oauth.google.authorize_access_token()
        # The user's profile information is in the ID token
        user_info = oauth.google.parse_id_token(token)
        session['user'] = user_info

        # IMPORTANT: Use the stable Google user ID as the visitor_id for
        # consistent personalization and event tracking for logged-in users.
        session['visitor_id'] = user_info['sub']

        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error during Google OAuth callback: {e}\n{traceback.format_exc()}")
        return redirect(url_for('index')) # Redirect home on error


@app.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.pop('user', None)
    session['visitor_id'] = str(uuid.uuid4()) # Reset to a new anonymous ID
    return redirect(url_for('index'))


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
            # Convert the PredictionResult proto message to a dictionary.
            # This correctly handles all nested structures and types, including
            # the product metadata which is a Struct.
            result_dict = PredictResponse.PredictionResult.to_dict(result)

            # The product data is inside the 'metadata' dictionary.
            if 'product' in result_dict.get('metadata', {}):
                product_dict = result_dict['metadata']['product']

                # The .to_dict() method can add a "@type" field which is not
                # part of the Product proto schema and causes a ParseError.
                # We remove it before attempting to load it back into a Product message.
                product_dict.pop('@type', None)

                # Then, we serialize the dictionary to a JSON string to use the `Product.from_json`
                # helper, which correctly handles field name conversions (e.g., priceInfo -> price_info).
                product_json_str = json.dumps(product_dict)
                recommendations.append(Product.from_json(product_json_str))

    except (GoogleAPICallError, Exception) as e:
        error = str(e)
        print(f"Error getting recommendations: {e}\n{traceback.format_exc()}")
    
    # Pass the attribution token from the predict response to the template
    return render_template('index.html', recommendations=recommendations, error=error, event_type='home-page-view', attribution_token=response.attribution_token if 'response' in locals() else None)


@app.route('/about')
def about():
    """Renders the about page."""
    return render_template('about.html')


@app.route('/categories')
def categories_list():
    """Displays a list of all product categories."""
    try:
        # Perform a search with an empty query and a facet spec for categories.
        # This is an efficient pattern to populate a category listing page.
        facet_spec = SearchRequest.FacetSpec(
            facet_key=SearchRequest.FacetSpec.FacetKey(key="categories", order_by="count desc"),
            # The UserEvent API allows a maximum of 250 pageCategories, so we cap the facet request here.
            limit=250
        )

        branch_path = SearchServiceClient.branch_path(
            project=config.PROJECT_ID,
            location=config.LOCATION,
            catalog=config.CATALOG_ID,
            branch="default_branch"
        )

        search_request = SearchRequest(
            placement=search_placement,
            branch=branch_path,
            query="", # Empty query
            visitor_id=session.get('visitor_id'),
            page_size=0, # We only need the facets, not the results
            facet_specs=[facet_spec],
        )

        search_pager = search_client.search(search_request)
        search_response = next(search_pager.pages)

        # The first (and only) facet in the response will be our categories
        category_facet = search_response.facets[0] if search_response.facets else None

        # For a 'category-page-view' event, we need to supply the categories.
        # In this case, it's all the categories being listed on the page.
        page_categories = []
        if category_facet:
            page_categories = [v.value for v in category_facet.values]
        page_categories_json = json.dumps(page_categories)

        return render_template('categories.html', category_facet=category_facet, error=None, event_type='category-page-view', page_categories_json=page_categories_json)

    except Exception as e:
        print(f"Error fetching category list: {e}\n{traceback.format_exc()}")
        # Pass event type and empty categories json on error to avoid breaking the event tracker
        return render_template('categories.html', error=str(e), category_facet=None, event_type='category-page-view', page_categories_json='[]')


@app.route('/browse/<path:category_name>')
def browse_category(category_name):
    """
    Performs a browse search for a specific category using Vertex AI Search.
    This is characterized by an empty query and a specified page_categories field.
    """
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    if page < 1:
        page = 1

    page_size = 20
    offset = (page - 1) * page_size

    # --- Handle Facets ---
    # For a browse request, the primary filter is the category itself.
    # Additional filters from user interaction are ANDed with it.
    facet_filters = [f'categories: ANY("{category_name}")']
    selected_facets = {}
    processed_keys = {'page'}

    for key in request.args:
        if key not in processed_keys:
            values = request.args.getlist(key)
            selected_facets[key] = values
            # This logic is similar to the main search page for consistency
            if key in ['price', 'rating']:
                range_filters = []
                filter_key = 'price' if key == 'price' else key
                for v in values:
                    try:
                        min_val_str, max_val_str = v.split('-', 1)
                        range_filter_parts = []
                        if min_val_str: range_filter_parts.append(f'{filter_key} >= {float(min_val_str)}')
                        if max_val_str: range_filter_parts.append(f'{filter_key} < {float(max_val_str)}')
                        if range_filter_parts: range_filters.append(f"({' AND '.join(range_filter_parts)})")
                    except (ValueError, IndexError): continue
                if range_filters: facet_filters.append(f"({' OR '.join(range_filters)})")
            else:
                filter_values = ', '.join([f'"{v}"' for v in values])
                facet_filters.append(f'{key}: ANY({filter_values})')
            processed_keys.add(key)

    search_filter = " AND ".join(facet_filters)

    # --- Build Search Request for BROWSE ---
    facet_specs = [
        SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="brands", order_by="count desc")),
        SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="categories", order_by="count desc")),
        SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="colorFamilies", order_by="count desc")),
        SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="price")),
        SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="rating")),
    ]
    branch_path = SearchServiceClient.branch_path(project=config.PROJECT_ID, location=config.LOCATION, catalog=config.CATALOG_ID, branch="default_branch")

    search_request = SearchRequest(
        placement=search_placement, branch=branch_path, query="", page_categories=[category_name],
        visitor_id=session.get('visitor_id'), page_size=page_size, offset=offset,
        facet_specs=facet_specs, filter=search_filter,
    )

    try:
        search_pager = search_client.search(search_request)
        search_response = next(search_pager.pages)
        total_pages = int(math.ceil(search_response.total_size / page_size)) if search_response.total_size > 0 else 0
        results_for_js = [SearchResponse.SearchResult.to_dict(r) for r in search_response.results]
        page_categories_json = json.dumps([category_name]) # The category being browsed
        return render_template('browse_results.html',
            results=search_response.results,
            facets=search_response.facets,
            selected_facets=selected_facets,
            results_json=results_for_js,
            category_name=category_name,
            event_type='search',
            page_categories_json=page_categories_json,
            search_filter=search_filter,
            current_page=page,
            total_pages=total_pages,
            total_results=search_response.total_size,
            page_size=page_size,
            attribution_token=search_response.attribution_token
        )
    except Exception as e:
        print(f"Error during browse search for category '{category_name}': {e}\n{traceback.format_exc()}")
        return render_template('browse_results.html',
            error=str(e), category_name=category_name,
            event_type='search', page_categories_json='[]', facets=[], selected_facets={},
            current_page=1, total_pages=0, total_results=0
        )

@app.route('/search')
def search():
    """
    Performs a search using the Vertex AI Search for Commerce Retail API.
    """
    query = request.args.get('query', '').strip()
    attribution_token = request.args.get('attribution_token')
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    if page < 1:
        page = 1

    page_size = 20
    offset = (page - 1) * page_size

    # Add server-side validation to match the client-side minlength attribute
    if len(query) < 2:
        return redirect(url_for('index'))
 
    # --- Handle Facets ---
    facet_filters = []
    selected_facets = {}
    # Use a set to avoid reprocessing keys when using getlist
    processed_keys = {'query', 'expand', 'page', 'attribution_token'}

    for key in request.args:
        if key not in processed_keys:
            values = request.args.getlist(key)
            selected_facets[key] = values

            # Check if the key is for a numerical facet we defined
            if key in ['price', 'rating']:
                # For numerical facets, we expect values like "10.00-25.00"
                # and build filters like "(price >= 10.00 AND price < 25.00)".
                # Multiple selected ranges for the same key are ORed together.
                range_filters = []

                # The API's filter syntax for price is just 'price', not the full path.
                filter_key = 'price' if key == 'price' else key

                for v in values:
                    try:
                        min_val_str, max_val_str = v.split('-', 1)
                        range_filter_parts = []
                        if min_val_str:
                            range_filter_parts.append(f'{filter_key} >= {float(min_val_str)}')
                        if max_val_str:
                            # The API's interval is exclusive for the maximum.
                            range_filter_parts.append(f'{filter_key} < {float(max_val_str)}')
                        if range_filter_parts:
                            range_filters.append(f"({' AND '.join(range_filter_parts)})")
                    except (ValueError, IndexError):
                        # Ignore malformed range values
                        continue
                if range_filters:
                    facet_filters.append(f"({' OR '.join(range_filters)})")
            else:
                # Existing logic for textual facets
                filter_values = ', '.join([f'"{v}"' for v in values])
                facet_filters.append(f'{key}: ANY({filter_values})')

            processed_keys.add(key)

    # Combine all facet filters with AND
    search_filter = " AND ".join(facet_filters) if facet_filters else ""

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

    # Define explicit facet specifications instead of using dynamic faceting.
    # This gives more control over which facets are returned and how they are ordered.
    facet_specs = [
        SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="brands", order_by="count desc")),
        SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="categories", order_by="count desc")),
        SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="colorFamilies", order_by="count desc")),
        # For numerical facets like price and rating, we can let the API generate dynamic intervals
        # based on the distribution of values in the search results.
        SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="price")),
        SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="rating")),
    ]

    # # --- Handle Sorting ---
    # sort_map = {
    #     # 'relevance' is the default and is handled by omitting the order_by field.
    #     'price_asc': 'price_info.price asc',
    #     'price_desc': 'price_info.price desc',
    # }
    # # Get the API-specific sort string. If sort_by is 'relevance' or invalid,
    # # this will be None, correctly triggering the API's default relevance sort.
    # order_by_value = sort_map.get(sort_by)

    # The branch to search. This should match the branch where product data is indexed.
    # By default, product data is ingested into branch '0' (the default_branch).
    branch_path = SearchServiceClient.branch_path(
        project=config.PROJECT_ID,
        location=config.LOCATION,
        catalog=config.CATALOG_ID,
        branch="default_branch"
    )

    search_request = SearchRequest(
        placement=search_placement,
        branch=branch_path,
        query=query,
        visitor_id=session.get('visitor_id'),
        page_size=page_size,
        offset=offset,
        query_expansion_spec=query_expansion_spec,
        facet_specs=facet_specs,
        filter=search_filter,
        # order_by=order_by_value,
    )

    # --- Call the Retail API ---
    try:
        # The search method returns a SearchPager. We need to get the first page
        # of the response to access metadata like facets and total_size.
        search_pager = search_client.search(search_request)
        search_response = next(search_pager.pages)
 
        total_pages = 0
        if search_response.total_size > 0:
            total_pages = int(math.ceil(search_response.total_size / page_size))

        # The search_response.results is a list of proto messages, not directly
        # JSON serializable. Convert them to dicts for the event tracker.
        results_for_js = [SearchResponse.SearchResult.to_dict(r) for r in search_response.results]
        return render_template(
            'search_results.html',
            results=search_response.results,
            facets=search_response.facets,
            selected_facets=selected_facets,
            search_filter=search_filter,
            results_json=results_for_js,
            query=query,
            use_expansion=use_expansion,
            event_type='search',
            current_page=page,
            total_pages=total_pages,
            total_results=search_response.total_size,
            page_size=page_size,
            # This is the NEW token for actions taken on this page (e.g., clicking a product)
            attribution_token=search_response.attribution_token,
            # This is the OLD token from the previous page, used for the search event itself.
            search_event_attribution_token=attribution_token,
            # sort_by=sort_by
        )
    except Exception as e:
        print(f"Error during search: {e}\n{traceback.format_exc()}")
        return render_template('search_results.html', error=str(e), query=query, use_expansion=use_expansion, event_type='search', facets=[], selected_facets={}, current_page=1, total_pages=0, total_results=0) #, sort_by='relevance')


@app.route('/product/<string:product_id>')
def product_detail(product_id):
    """
    Fetches and displays the details for a single product.
    """
    attribution_token = request.args.get('attribution_token')
    product_name = product_client.product_path(
        project=config.PROJECT_ID,
        location=config.LOCATION,
        catalog=config.CATALOG_ID,
        branch="default_branch", # Search and get operations should use the same branch, typically '0' (default_branch).
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
            event_type='detail-page-view',
            attribution_token=attribution_token
        )
    except Exception as e:
        print(f"Error fetching product details: {e}\n{traceback.format_exc()}")
        return render_template('product_detail.html', error=str(e))


@app.route('/chat', methods=['GET'])
def chat():
    """Renders the conversational commerce chat interface."""
    # Initialize chat state in session if it doesn't exist
    if 'chat_history' not in session:
        session['chat_history'] = []
        session['conversation_id'] = ""  # Start with an empty conversation ID

    # For GET requests, just render the chat history from the session.
    return render_template(
        'chat.html',
        chat_history=session.get('chat_history', []),
        conversation_id=session.get('conversation_id', '')
    )


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handles asynchronous chat requests."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    query = data.get('query', '').strip()
    conversation_id = data.get('conversation_id', '')

    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    # Add user's message to session history for persistence across reloads
    if 'chat_history' not in session:
        session['chat_history'] = []
    session['chat_history'].append({'is_user': True, 'text': query})

    try:
        # Build the conversational search request
        branch_path = SearchServiceClient.branch_path(
            project=config.PROJECT_ID,
            location=config.LOCATION,
            catalog=config.CATALOG_ID,
            branch="default_branch"
        )

        conv_search_request = ConversationalSearchRequest(
            placement=conversational_placement,
            branch=branch_path,
            query=query,
            visitor_id=session.get('visitor_id'),
            conversation_id=conversation_id,
            conversational_filtering_spec=ConversationalSearchRequest.ConversationalFilteringSpec(
                conversational_filtering_mode=ConversationalSearchRequest.ConversationalFilteringSpec.Mode.DISABLED
            )
        )

        streaming_response = conversational_search_client.conversational_search(request=conv_search_request)

        # Aggregate the streaming response
        response = ConversationalSearchResponse()
        for chunk in streaming_response:
            response._pb.MergeFrom(chunk._pb)

        new_conversation_id = response.conversation_id

        # De-duplicate refined queries while preserving order, as the streaming
        # API can sometimes send the same suggestions in multiple chunks.
        unique_refined_queries = []
        seen_queries = set()
        for rs in response.refined_search:
            if rs.query not in seen_queries:
                unique_refined_queries.append(rs.query)
                seen_queries.add(rs.query)

        # --- Process the response for the template ---
        bot_response = {
            'is_user': False,
            'text': response.conversational_text_response,
            'followup_question': response.followup_question.followup_question if response.followup_question else None,
            'refined_queries': unique_refined_queries,
            'products': []
        }

        # If the AI provides refined search queries, fetch products for the first one
        if response.refined_search:
            refined_query = response.refined_search[0].query

            # Define the same facet specifications as the main search page.
            # This signals to the API that we need rich product data,
            # which is crucial for getting fields like priceInfo.
            facet_specs = [
                SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="brands")),
                SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="categories")),
                SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="price")),
                SearchRequest.FacetSpec(facet_key=SearchRequest.FacetSpec.FacetKey(key="rating")),
            ]

            # Ensure query expansion is enabled to get full product details,
            # mirroring the behavior of the main search page. A more basic
            # request may result in fewer fields being returned.
            query_expansion_spec = SearchRequest.QueryExpansionSpec(
                condition=SearchRequest.QueryExpansionSpec.Condition.AUTO,
                pin_unexpanded_results=True
            )

            search_req = SearchRequest(
                placement=search_placement,
                branch=branch_path,
                query=refined_query,
                visitor_id=session.get('visitor_id'),
                page_size=3,
                query_expansion_spec=query_expansion_spec,
                facet_specs=facet_specs,
            )
            search_pager = search_client.search(request=search_req)
            
            products_for_session = []
            for r in search_pager.results:
                product_dict = SearchResponse.SearchResult.to_dict(r)
                # --- DEBUG --- Print the full product dictionary from the API
                ## print(f"DEBUG (Chat API): Product data received: {json.dumps(product_dict, indent=2)}")
                # The product data is nested inside the 'product' key of the search result.
                # We can simplify the logic by assigning this dictionary directly.
                simplified_product = {
                    'id': product_dict.get('id'),
                    'product': product_dict.get('product', {})
                }
                products_for_session.append(simplified_product)
            bot_response['products'] = products_for_session

        # Add bot's response to session history
        session['chat_history'].append(bot_response)
        session.modified = True

        # Return the bot's response and new conversation ID to the client
        return jsonify({
            'bot_response': bot_response,
            'conversation_id': new_conversation_id
        })

    except (GoogleAPICallError, Exception) as e:
        error_message = "Sorry, I encountered an error. Please try again."
        # Add error to session history
        session['chat_history'].append({'is_user': False, 'text': error_message})
        session.modified = True
        print(f"Error during conversational search: {e}\n{traceback.format_exc()}")
        # Return error to client
        return jsonify({"error": str(e), "bot_response": {'text': error_message}}), 500


@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    """Clears the chat history and conversation ID from the session."""
    session.pop('chat_history', None)
    session.pop('conversation_id', None)
    return redirect(url_for('chat'))


@app.route('/api/autocomplete')
def autocomplete():
    """Provides search suggestions based on the user's partial query."""
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])

    # The SearchServiceClient does not have a 'catalog_path' helper.
    # We can use the product_client or user_event_client to build the path.
    catalog_path = user_event_client.catalog_path(
        project=config.PROJECT_ID,
        location=config.LOCATION,
        catalog=config.CATALOG_ID
    )

    complete_query_request = CompleteQueryRequest(
        catalog=catalog_path,
        query=query,
        visitor_id=session.get('visitor_id'),
        # By default, the API will use a dataset generated from user events.
    )

    try:
        response = completion_client.complete_query(request=complete_query_request)
        # Extract just the suggestion text from the response
        suggestions = [result.suggestion for result in response.completion_results]
        # Add a log to see what the API is returning in the backend console
        print(f"Autocomplete suggestions for '{query}': {suggestions}")
        return jsonify(suggestions)
    except Exception as e:
        print(f"Error during autocomplete: {e}")
        return jsonify([]) # Return empty list on error to prevent frontend issues


@app.route('/api/track_event', methods=['POST'])
def track_event():
    """
    Receives a user event from the client and writes it to the Retail API.
    This provides a secure, server-side event ingestion mechanism.
    """
    event_data = request.get_json()
    if not event_data:
        return {"error": "Invalid JSON payload"}, 400

    # --- Enrich event with server-side data ---
    # Create userInfo object, which is required for high-quality event data.
    user_info = {
        "userAgent": request.user_agent.string,
        "ipAddress": request.remote_addr
    }
    # If the user is logged in, associate the event with their stable user ID.
    if session.get('user'):
        user_info["userId"] = session['user']['sub']
    
    # Add the enriched userInfo object to the event payload.
    event_data['userInfo'] = user_info
    # --- End enrichment ---

    # --- Server-side data correction for specific event types ---
    # If the event is a category-page-view and the client didn't send
    # pageCategories, we fetch them here to ensure the event is valid.
    # This makes the system more robust against client-side issues.
    if event_data.get("eventType") == "category-page-view" and "pageCategories" not in event_data:
        print("Enriching category-page-view event with pageCategories on the server.")
        try:
            # This logic is the same as in the `categories_list` route.
            facet_spec = SearchRequest.FacetSpec(
                facet_key=SearchRequest.FacetSpec.FacetKey(key="categories"),
                limit=250  # Match the limit used on the categories page itself.
            )
            branch_path = SearchServiceClient.branch_path(
                project=config.PROJECT_ID, location=config.LOCATION,
                catalog=config.CATALOG_ID, branch="default_branch"
            )
            search_request = SearchRequest(
                placement=search_placement, branch=branch_path, query="",
                visitor_id=event_data.get('visitorId'), page_size=0, facet_specs=[facet_spec]
            )
            search_response = next(search_client.search(search_request).pages)
            if search_response.facets:
                event_data["pageCategories"] = [v.value for v in search_response.facets[0].values]
        except Exception as e:
            print(f"Could not enrich category-page-view event: {e}")

    print(f"Received and enriched event data: {json.dumps(event_data, indent=2)}")

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
    """Adds a product to the cart and tracks the 'add-to-cart' event."""
    product_id = request.form.get('product_id')
    product_title = request.form.get('product_title')
    price_str = request.form.get('product_price')
    product_image = request.form.get('product_image')
    attribution_token = request.form.get('attribution_token')

    try:
        # More robustly handle conversion from form string to float.
        product_price = float(price_str)
    except (ValueError, TypeError):
        # Default to 0.0 if price is missing, not a valid number, or None.
        product_price = 0.0

    if not product_id:
        return redirect(url_for('index'))

    # --- Track add-to-cart event on Server-Side for Reliability ---
    try:
        parent = user_event_client.catalog_path(
            project=config.PROJECT_ID,
            location=config.LOCATION,
            catalog=config.CATALOG_ID
        )

        product_details = [{
            "product": {"id": product_id},
            "quantity": 1
        }]

        event_payload = {
            "eventType": "add-to-cart",
            "visitorId": session.get('visitor_id'),
            "cartId": session.get('visitor_id'), # Use visitorId as a stable cartId
            "productDetails": product_details,
            "uri": request.referrer or url_for('index', _external=True), # Page where add was clicked
        }
        if attribution_token:
            event_payload["attributionToken"] = attribution_token

        # Add userInfo for a high-quality server-side event
        user_info = {
            "userAgent": request.user_agent.string,
            "ipAddress": request.remote_addr
        }
        if session.get('user'):
            user_info["userId"] = session['user']['sub']
        event_payload['userInfo'] = user_info

        user_event = UserEvent.from_json(json.dumps(event_payload))
        write_request = WriteUserEventRequest(parent=parent, user_event=user_event)
        user_event_client.write_user_event(request=write_request)
        print(f"Successfully wrote server-side event: add-to-cart for visitor {session.get('visitor_id')}")
    except Exception as e:
        # Log the error but don't block the user from completing the purchase
        print(f"Error writing server-side add-to-cart event: {e}\n{traceback.format_exc()}")

    # Add item to cart
    cart = session.get('cart', {})

    if product_id in cart:
        # Item exists, just increment quantity
        cart[product_id]['quantity'] += 1
    else:
            # Add new item to cart, storing only essential data to keep session small
        cart[product_id] = {
            'price': product_price,
            'quantity': 1
        }
    session['cart'] = cart

    # Update total
    session['cart_total'] = sum(item['price'] * item['quantity'] for item in cart.values())

    # Flash a success message to be displayed on the next page
    cart_url = url_for('view_cart')
    flash(f"'{product_title}' has been added to your <a href=\"{cart_url}\">cart</a>.", 'success')

    # Redirect back to the page the user came from for a smoother experience
    return redirect(request.referrer or url_for('index'))


@app.route('/cart')
def view_cart():
    """Displays the shopping cart."""
    cart_from_session = session.get('cart', {})
    total = session.get('cart_total', 0.0)

    if not cart_from_session:
        return render_template('cart.html', cart={}, total=total, event_type='shopping-cart-page-view')

    rich_cart_items = {}
    for product_id, item_data in cart_from_session.items():
        try:
            product_name = product_client.product_path(
                project=config.PROJECT_ID,
                location=config.LOCATION,
                catalog=config.CATALOG_ID,
                branch="default_branch",
                product=product_id
            )
            product = product_client.get_product(name=product_name)

            rich_cart_items[product_id] = {
                'id': product.id,
                'title': product.title,
                'image': product.images[0].uri if product.images else '',
                'price': item_data['price'],
                'quantity': item_data['quantity']
            }
        except Exception as e:
            print(f"Error fetching product {product_id} for cart view: {e}")
            # If a product can't be fetched, we'll still show it with basic info.
            rich_cart_items[product_id] = {
                'id': product_id, 'title': 'Product not available', 'image': '',
                'price': item_data['price'], 'quantity': item_data['quantity']
            }

    return render_template('cart.html', cart=rich_cart_items, total=total, event_type='shopping-cart-page-view')


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
    """Simulates checkout, tracks the purchase event, and redirects to a confirmation page."""
    cart_from_session = session.get('cart', {})
    total_at_checkout = session.get('cart_total', 0.0)
    transaction_id = str(uuid.uuid4())
    visitor_id = session.get('visitor_id')

    # We need to enrich the cart items with titles for the confirmation page.
    cart_at_checkout = []
    if cart_from_session:
        for product_id, item_data in cart_from_session.items():
            try:
                product_name = product_client.product_path(
                    project=config.PROJECT_ID, location=config.LOCATION,
                    catalog=config.CATALOG_ID, branch="default_branch", product=product_id
                )
                product = product_client.get_product(name=product_name)
                cart_at_checkout.append({
                    'id': product_id,
                    'title': product.title,
                    'quantity': item_data['quantity']
                })
            except Exception as e:
                print(f"Error fetching product {product_id} for checkout: {e}")
                cart_at_checkout.append({
                    'id': product_id, 'title': 'Unknown Product', 'quantity': item_data['quantity']
                })

    # --- Track Purchase Event on Server-Side for Reliability ---
    if cart_at_checkout: # Only track if there was something in the cart
        try:
            parent = user_event_client.catalog_path(
                project=config.PROJECT_ID,
                location=config.LOCATION,
                catalog=config.CATALOG_ID
            )

            product_details = []
            # Use the original cart data from session which includes price
            for product_id, item_data in cart_from_session.items():
                product_details.append({
                    "product": {
                        "id": product_id,
                        # Include priceInfo for revenue optimization models
                        "priceInfo": {
                            "price": item_data.get('price', 0.0),
                            "currencyCode": "USD"
                        }
                    },
                    "quantity": item_data.get('quantity', 0)
                })

            purchase_transaction = {
                "id": transaction_id,
                "revenue": total_at_checkout,
                "currencyCode": "USD" # Assuming USD
            }

            user_event_payload = {
                "eventType": "purchase-complete",
                "visitorId": visitor_id,
                "cartId": visitor_id, # Use visitorId as a stable cartId
                "productDetails": product_details,
                "purchaseTransaction": purchase_transaction,
                "uri": url_for('checkout', _external=True)
            }

            # Add userInfo for a high-quality server-side event
            user_info = {
                "userAgent": request.user_agent.string,
                "ipAddress": request.remote_addr
            }
            if session.get('user'):
                user_info["userId"] = session['user']['sub']
            user_event_payload['userInfo'] = user_info

            user_event = UserEvent.from_json(json.dumps(user_event_payload))
            write_request = WriteUserEventRequest(parent=parent, user_event=user_event)
            user_event_client.write_user_event(request=write_request)
            print(f"Successfully wrote server-side event: purchase-complete for visitor {visitor_id}")
        except Exception as e:
            # Log the error but don't block the user from completing the purchase
            print(f"Error writing server-side purchase event: {e}\n{traceback.format_exc()}")

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
    """Displays the purchase confirmation page."""
    last_order = session.get('last_order')
    if not last_order:
        return redirect(url_for('index'))

    # Clear the last order from session after displaying it to prevent re-submission on refresh.
    session.pop('last_order', None)
    return render_template('purchase_confirmation.html', order=last_order, event_type='purchase-complete')

if __name__ == '__main__':
    # This block is for running the app directly with `python app.py`
    # For production, use a WSGI server like Gunicorn.
    app.run(debug=True, port=5000)