/**
 * Vibe Commerce Event Tracker
 *
 * This script provides helper functions to send user events to a secure
 * backend endpoint, which then forwards them to the Google Cloud Retail API.
 */

const VibeTracker = {
  _eventQueue: [],
  _isSending: false,

  init(config) {
    this.visitorId = config.visitorId;
    console.log('Server-side Event Tracker Initialized for visitor:', this.visitorId);

    // Add a listener to flush the queue when the user navigates away.
    // This uses navigator.sendBeacon for a more reliable delivery.
    window.addEventListener('beforeunload', () => {
      if (this._eventQueue.length > 0) {
        console.log(`Sending ${this._eventQueue.length} remaining events via sendBeacon.`);
        const payload = this._eventQueue.map(event => ({...event, visitorId: this.visitorId}));
        // Note: sendBeacon sends all events in one go.
        // For a high-traffic site, you might send them individually or in batches.
        const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
        navigator.sendBeacon('/api/track_event', blob);
      }
    });
  },

  _flushQueue() {
    if (this._isSending || this._eventQueue.length === 0) {
      return;
    }
    this._isSending = true;
    const eventData = this._eventQueue.shift();

    fetch('/api/track_event', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(eventData),
    })
    .then(response => {
      if (!response.ok) {
        console.error('Failed to track event:', eventData, response);
      }
    })
    .catch(error => {
      console.error('Error sending event to backend:', error);
    })
    .finally(() => {
      this._isSending = false;
      this._flushQueue(); // Process next item in queue
    });
  },

  /**
   * Logs an event to the Retail API.
   * @param {object} eventData - The user event payload.
   */
  _logEvent(eventData) {
    const payload = { ...eventData, visitorId: this.visitorId };
    console.log("Queuing event:", payload);
    this._eventQueue.push(payload);
    this._flushQueue();

    // Update debug footer with the latest event type
    const eventTypeEl = document.getElementById('debug-event-type');
    if (eventTypeEl) {
      eventTypeEl.textContent = payload.eventType;
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
