/**
 * Vibe Commerce Event Tracker
 *
 * This script provides helper functions to send user events to the
 * Google Cloud Retail API via v2_event.js.
 */

const VibeTracker = {
  _eventQueue: [],
  _isGreReady: false,
  _checkInterval: null,

  init(config) {
    this.visitorId = config.visitorId;
    console.log('Real-time Event Tracker Initialized for visitor:', this.visitorId);
    this._startGreCheck();
  },

  _startGreCheck() {
    this._checkInterval = setInterval(() => {
      // The sign that v2_event.js is ready is that _gre is no longer a simple array.
      if (typeof _gre !== 'undefined' && !Array.isArray(_gre)) {
        this._isGreReady = true;
        console.log("Google Retail Event library is ready. Processing queue.");
        this._flushQueue();
        clearInterval(this._checkInterval);
      }
    }, 100); // Check every 100ms

    // Failsafe: stop checking after a few seconds to prevent an infinite loop
    setTimeout(() => {
      if (!this._isGreReady) {
        console.error("Google Retail Event library did not initialize after 5 seconds. Events will not be sent.");
        clearInterval(this._checkInterval);
      }
    }, 5000);
  },

  _flushQueue() {
    while (this._eventQueue.length > 0) {
      const eventData = this._eventQueue.shift();
      console.log("Flushing event from queue:", eventData);
      _gre.push(['logEvent', eventData]);
    }
  },

  /**
   * Logs an event to the Retail API.
   * @param {object} eventData - The user event payload.
   */
  _logEvent(eventData) {
    const payload = { ...eventData, visitorId: this.visitorId };
    if (this._isGreReady) {
      console.log("Logging event directly:", payload);
      _gre.push(['logEvent', payload]);
    } else {
      console.log("Queuing event:", payload);
      this._eventQueue.push(payload);
    }
  },

  /**
   * Tracks a 'home-page-view' event.
   */
  trackHomePageView() {
    this._logEvent({
      eventType: 'home-page-view',
    });
  },

  /**
   * Tracks a 'search' event.
   * @param {string} query - The search query entered by the user.
   * @param {Array<object>} results - The search results array.
   */
  trackSearchView(query, results) {
    const productDetails = results.map(result => ({
      product: { id: result.id } // Use the top-level ID from the search result
    }));

    this._logEvent({
      eventType: 'search',
      searchQuery: query,
      productDetails: productDetails,
    });
  },

  /**
   * Tracks a 'detail-page-view' event.
   * @param {object} product - The product being viewed.
   */
  trackDetailPageView(product) {
    if (!product || !product.id) return;

    this._logEvent({
      eventType: 'detail-page-view',
      productDetails: [{
        product: { id: product.id }
      }],
    });
  },

  /**
   * Tracks an 'add-to-cart' event.
   * @param {object} product - The product being added to the cart.
   */
  trackAddToCart(product) {
    if (!product || !product.id) return;

    this._logEvent({
      eventType: 'add-to-cart',
      productDetails: [{
        product: { id: product.id },
        quantity: 1 // Assuming quantity is always 1 for this action
      }],
    });
  },

  /**
   * Tracks a 'shopping-cart-page-view' event.
   * @param {Array<object>} cartItems - The items currently in the cart.
   */
  trackShoppingCartView(cartItems) {
    const productDetails = cartItems.map(p => ({
      product: { id: p.id },
      quantity: p.quantity
    }));

    this._logEvent({
      eventType: 'shopping-cart-page-view',
      productDetails: productDetails,
    });
  },

  /**
   * Tracks a 'remove-from-cart' event.
   * @param {object} product - The product being removed from the cart.
   */
  trackRemoveFromCart(product) {
    if (!product || !product.id) return;

    this._logEvent({
      eventType: 'remove-from-cart',
      productDetails: [{
        product: { id: product.id },
        quantity: product.quantity // The quantity that was in the cart
      }],
    });
  },

  /**
   * Tracks a 'purchase-complete' event.
   * @param {object} orderDetails - An object containing the purchased items and transaction details.
   */
  trackPurchaseComplete(orderDetails) {
    const productDetails = orderDetails.items.map(p => ({
      product: { id: p.id },
      quantity: p.quantity
    }));

    this._logEvent({
      eventType: 'purchase-complete',
      productDetails: productDetails,
      purchaseTransaction: {
        id: orderDetails.transaction_id,
        revenue: orderDetails.total,
        currencyCode: 'USD' // Assuming USD
      }
    });
  }
};
