// static/js/event_tracker.js

// A centralized tracker for sending user events to the backend.
const VibeTracker = {
    visitorId: null,
    pageViewId: crypto.randomUUID(), // Generate a unique ID for this page view.

    init(config) {
        this.visitorId = config.visitorId;
    },

    // A generic method to track any event type.
    trackEvent(payload) {
        if (!this.visitorId) {
            console.error("VibeTracker not initialized. VisitorId is missing.");
            return;
        }
        // Enrich payload with standard fields on the client-side.
        payload.visitorId = this.visitorId;
        payload.pageViewId = this.pageViewId;
        payload.uri = window.location.href;
        payload.referrerUri = document.referrer;

        // For debugging, log the event being sent to the browser console.
        console.log('VibeTracker: Tracking event', JSON.stringify(payload, null, 2));

        // Use fetch with keepalive to ensure the request is sent even if the page unloads.
        fetch('/api/track_event', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
            keepalive: true
        }).catch(error => console.error('VibeTracker: Error tracking event:', error));
    },

    // --- Specific Event Helper Methods ---

    trackHomePageView() {
        this.trackEvent({ eventType: 'home-page-view' });
    },

    trackCategoryPageView() {
        this.trackEvent({ eventType: 'category-page-view' });
    },

    trackSearchView(query, results, attributionToken, filter) {
        const payload = {
            eventType: 'search',
            searchQuery: query,
            productDetails: results.map(r => ({ product: { id: r.id } }))
        };
        if (attributionToken) {
            payload.attributionToken = attributionToken;
        }
        if (filter) {
            payload.filter = filter;
        }
        this.trackEvent(payload);
    },

    trackBrowseView(pageCategories, results, attributionToken, filter) {
        const payload = {
            eventType: 'search', // Browse is a type of search event
            searchQuery: '',
            pageCategories: pageCategories,
            productDetails: results.map(r => ({ product: { id: r.id } })),
        };
        if (filter) {
            payload.filter = filter;
        }
        if (attributionToken) {
            payload.attributionToken = attributionToken;
        }
        this.trackEvent(payload);
    },

    trackDetailPageView(product, attributionToken) {
        const payload = {
            eventType: 'detail-page-view',
            productDetails: [{
                product: product // The product object itself
            }]
        };
        if (attributionToken) {
            payload.attributionToken = attributionToken;
        }
        this.trackEvent(payload);
    },

    trackShoppingCartView(cartItems) {
        if (!cartItems || cartItems.length === 0) return;
        this.trackEvent({
            eventType: 'shopping-cart-page-view',
            cartId: this.visitorId, // Use visitorId as a stable cartId
            productDetails: cartItems.map(item => ({
                product: { id: item.id },
                quantity: item.quantity
            }))
        });
    }
};