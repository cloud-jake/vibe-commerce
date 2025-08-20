/**
 * Vibe Commerce Event Tracker
 *
 * This script provides helper functions to send user events to the
 * Google Cloud Retail API via gtag.js.
 */

const VibeTracker = {
  init(config) {
    this.visitorId = config.visitorId;
    this.catalogId = config.catalogId;
    this.projectId = config.projectId;
    console.log('Event Tracker Initialized for visitor:', this.visitorId);
  },

  /**
   * Maps a product object from the Flask app to the format required by the Retail API.
   * @param {object} product - The product object.
   * @returns {object} A formatted product detail object.
   */
  _mapProduct(product) {
    if (!product || !product.id) {
      return null;
    }
    return {
      'id': product.id,
      'name': product.title, // Optional, but good for debugging
    };
  },

  /**
   * Tracks a 'home-page-view' event.
   */
  trackHomePageView() {
    console.log("Tracking: home-page-view");
    gtag('event', 'view_item_list', {
      'event_category': 'engagement',
      'event_label': 'home_page_view',
      'items': [] // Required for this event type in gtag.js
    });
  },

  /**
   * Tracks a 'search' event.
   * @param {string} query - The search query entered by the user.
   * @param {Array<object>} results - The search results array.
   */
  trackSearchView(query, results) {
    console.log(`Tracking: search for query "${query}"`);
    const items = results.map(r => this._mapProduct(r.product)).filter(p => p);
    gtag('event', 'search', {
      'search_term': query,
      'items': items
    });
  },

  /**
   * Tracks a 'detail-page-view' event.
   * @param {object} product - The product being viewed.
   */
  trackDetailPageView(product) {
    console.log(`Tracking: detail-page-view for product "${product.id}"`);
    const item = this._mapProduct(product);
    if (item) {
      gtag('event', 'view_item', {
        'items': [item]
      });
    }
  },

  /**
   * Tracks an 'add-to-cart' event.
   * @param {object} product - The product being added to the cart.
   */
  trackAddToCart(product) {
    console.log(`Tracking: add-to-cart for product "${product.id}"`);
    const item = this._mapProduct(product);
    if (item) {
      item.quantity = 1; // Assuming quantity is always 1 for this action
      gtag('event', 'add_to_cart', {
        'items': [item]
      });
    }
  },

  /**
   * Tracks a 'shopping-cart-page-view' event.
   * @param {Array<object>} cartItems - The items currently in the cart.
   */
  trackShoppingCartView(cartItems) {
    console.log("Tracking: shopping-cart-page-view");
    const items = cartItems.map(p => ({
      'id': p.id,
      'name': p.title,
      'quantity': p.quantity
    }));
    gtag('event', 'view_cart', {
      'items': items
    });
  },

  /**
   * Tracks a 'remove-from-cart' event.
   * @param {object} product - The product being removed from the cart.
   */
  trackRemoveFromCart(product) {
    console.log(`Tracking: remove-from-cart for product "${product.id}"`);
    const item = this._mapProduct(product);
    if (item) {
      item.quantity = product.quantity; // The quantity that was in the cart
      gtag('event', 'remove_from_cart', {
        'items': [item]
      });
    }
  },

  /**
   * Tracks a 'purchase-complete' event.
   * @param {object} orderDetails - An object containing the purchased items and transaction details.
   */
  trackPurchaseComplete(orderDetails) {
    console.log(`Tracking: purchase-complete for transaction "${orderDetails.transaction_id}"`);
    const items = orderDetails.items.map(p => ({
      'id': p.id,
      'name': p.title,
      'price': p.price,
      'quantity': p.quantity
    }));

    gtag('event', 'purchase', {
      'transaction_id': orderDetails.transaction_id,
      'value': orderDetails.total,
      'currency': 'USD', // Assuming USD
      'items': items
    });
  }
};

