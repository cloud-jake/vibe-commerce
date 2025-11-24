import json
import uuid
from flask import session, request, url_for
from google.cloud.retail_v2.types import UserEvent, UserInfo, WriteUserEventRequest
from google.cloud.retail_v2 import UserEventServiceClient
import config

# Initialize the User Event Service Client
user_event_client = UserEventServiceClient()

def process_facets(facets_from_api, selected_facets):
    """
    Converts the facet protobuf objects from the API into a more
    template-friendly list of dictionaries with a consistent structure.
    This helps prevent client-side JS errors from inconsistent data shapes.
    """
    processed_facets = []
    if not facets_from_api:
        return processed_facets

    # A map for creating user-friendly display names for facet keys.
    display_name_map = {
        'colorFamilies': 'Color',
        'categories': 'Category'
    }

    for facet in facets_from_api:
        facet_key = facet.key

        # Prepare a key for generating the display name, stripping "attributes."
        temp_display_key = facet_key
        if temp_display_key.lower().startswith('attributes.'):
            temp_display_key = temp_display_key.split('.', 1)[1]

        # Use the original facet_key for the map lookup, but the cleaned-up
        # key for the .title() fallback.
        display_name = display_name_map.get(facet_key, temp_display_key.title())

        processed_values = []
        for facet_value in facet.values:
            value_str = ""
            display_str = ""

            if facet_value.value:  # Textual facet
                value_str = facet_value.value
                display_str = facet_value.value
            elif facet_value.interval:  # Numerical facet
                min_val = facet_value.interval.minimum
                max_val = facet_value.interval.maximum
                
                # Create the value string for the URL parameter, e.g., "25.0-50.0"
                # The client-side parsing logic expects this format.
                value_str = f"{min_val or ''}-{max_val or ''}"

                # Create a user-friendly display string
                if facet_key == 'price':
                    if min_val is not None and max_val is not None:
                        display_str = f"${min_val:g} - ${max_val:g}"
                    elif min_val is not None:
                        display_str = f"Over ${min_val:g}"
                    elif max_val is not None:
                        display_str = f"Under ${max_val:g}"
                elif facet_key == 'rating':
                    if min_val is not None and max_val is not None:
                        display_str = f"{min_val:g} - {max_val:g} Stars"
                    elif min_val is not None:
                        display_str = f"{min_val:g}+ Stars"
                
            # Check if this facet value is currently selected
            is_selected = value_str in selected_facets.get(facet_key, [])

            # Only add the facet value if it has a count
            if facet_value.count > 0:
                processed_values.append({
                    'value': value_str, 'display': display_str,
                    'count': facet_value.count, 'selected': is_selected,
                })

        # Only add the facet group if it has values with counts
        if processed_values:
            processed_facets.append({
                'key': facet_key, 'display_name': display_name, 'values': processed_values
            })
            
    return processed_facets

def build_search_filter(request_args, exclude_keys=None):
    """
    Builds a filter string for the Retail API based on request arguments.
    """
    if exclude_keys is None:
        exclude_keys = set()
    
    facet_filters = []
    selected_facets = {}
    processed_keys = set(exclude_keys)

    for key in request_args:
        if key not in processed_keys:
            values = request_args.getlist(key)
            selected_facets[key] = values

            # Check if the key is for a numerical facet we defined
            if key in ['price', 'rating']:
                range_filters = []
                filter_key = 'price' if key == 'price' else key
                for v in values:
                    try:
                        min_val_str, max_val_str = v.split('-', 1)
                        range_filter_parts = []
                        if min_val_str:
                            range_filter_parts.append(f'{filter_key} >= {float(min_val_str)}')
                        if max_val_str:
                            range_filter_parts.append(f'{filter_key} < {float(max_val_str)}')
                        if range_filter_parts:
                            range_filters.append(f"({' AND '.join(range_filter_parts)})")
                    except (ValueError, IndexError):
                        continue
                if range_filters:
                    facet_filters.append(f"({' OR '.join(range_filters)})")
            else:
                filter_values = ', '.join([f'"{v}"' for v in values])
                facet_filters.append(f'{key}: ANY({filter_values})')

            processed_keys.add(key)

    search_filter = " AND ".join(facet_filters) if facet_filters else ""
    return search_filter, selected_facets

def get_support_links():
    """
    Constructs a dictionary of URLs for support-related intents.
    """
    default_routes = {
        "ORDER_SUPPORT": "orders",
        "DEALS_AND_COUPONS": "promotions",
        "STORE_RELEVANT": "stores",
        "RETAIL_SUPPORT": "support",
    }
    
    return {
        intent: config.SUPPORT_INTENT_URLS.get(intent) or url_for(route_name)
        for intent, route_name in default_routes.items()
    }

def track_event(event_type, visitor_id, user_info, uri, referrer, page_view_id=None, attribution_token=None, product_details=None, search_query=None, session_id=None):
    """
    Helper function to write user events to the Retail API.
    """
    try:
        parent = user_event_client.catalog_path(
            project=config.PROJECT_ID,
            location=config.LOCATION,
            catalog=config.CATALOG_ID
        )

        event_payload = {
            "eventType": event_type,
            "visitorId": visitor_id,
            "userInfo": user_info,
            "uri": uri,
            "referrerUri": referrer,
        }

        if page_view_id:
            event_payload["pageViewId"] = page_view_id
        if attribution_token:
            event_payload["attributionToken"] = attribution_token
        if product_details:
            event_payload["productDetails"] = product_details
        if search_query:
            event_payload["searchQuery"] = search_query
        if session_id:
            event_payload["sessionId"] = session_id

        user_event = UserEvent.from_json(json.dumps(event_payload))
        write_request = WriteUserEventRequest(parent=parent, user_event=user_event)
        user_event_client.write_user_event(request=write_request)
        print(f"Successfully wrote {event_type} event for visitor {visitor_id}")
        return True
    except Exception as e:
        print(f"Error writing {event_type} event: {e}")
        return False
