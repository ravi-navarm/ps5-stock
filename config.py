"""
Configuration for the PS5 stock tracker.  (v3)

v3 changes:
  - Blinkit / Zepto / Instamart added. Sony has sold the PS5 Slim through
    Blinkit since April 2024, so skipping quick commerce was a mistake.
  - Accessory filter is now plural-aware ("Console Covers" no longer reads
    as a console).
  - Games The Shop disabled -- its URL scheme changed, both known forms 404.
"""

# ---------------------------------------------------------------- delivery
PINCODES = ["500085", "500072"]          # Kukatpally / Nizampet, Hyderabad

# Quick-commerce stock is per dark-store, so those sites need coordinates.
# Approximate centroid of 500085 (Kukatpally).
QC_LAT, QC_LON = "17.4948", "78.3996"

QC_HEADERS = {
    "lat": QC_LAT,
    "lon": QC_LON,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ---------------------------------------------------------------- timing
POLL_SECONDS = 45
JITTER_SECONDS = 15
REQUEST_TIMEOUT = 20
MAX_WORKERS = 6
HEARTBEAT_HOURS = 12
REPEAT_ALERT_MINUTES = 30

# ---------------------------------------------------------------- prices
# A PS5 console in India is 40k-90k. Below the floor it's an accessory.
PRICE_FLOOR = 35000
PRICE_CEILING = 150000

# ---------------------------------------------------------------- signals
OUT_SIGNALS = [
    "out of stock", "sold out", "currently unavailable", "notify me",
    "coming soon", "temporarily unavailable", "out-of-stock", "outofstock",
    "notify when available", "back in stock soon", "not serviceable",
    "we don't know when or if this item will be back",
]

IN_SIGNALS = [
    "add to cart", "add to bag", "buy now", "add to basket",
    "in stock", "instock", "add-to-cart", "buy it now",
]

# A title must contain one of these to count as console hardware.
CONSOLE_MARKERS = ["console", "chassis", "digital edition"]

# ...and none of these. Matched with an optional trailing "s", so both
# "Cover" and "Covers" are excluded, while "Standard" still survives.
NOT_A_CONSOLE = [
    "controller", "dualsense", "headset", "pulse", "camera", "remote",
    "cover", "faceplate", "charging", "stand", "card", "earbud",
    "subscription", "voucher", "disc drive", "vertical", "skin", "plate",
]

# ---------------------------------------------------------------- targets
TARGETS = [
    # ================= SHOPIFY API (most reliable) =================
    {
        "name": "ShopAtSC - PS5 consoles (API)",
        "url": "https://shopatsc.com/collections/playstation-5-console/products.json?limit=250",
        "link": "https://shopatsc.com/collections/playstation-5-console",
        "type": "shopify",
        "enabled": True,
    },
    {
        "name": "ShopAtSC - all PlayStation 5 (API)",
        "url": "https://shopatsc.com/collections/playstation-5/products.json?limit=250",
        "link": "https://shopatsc.com/collections/playstation-5",
        "type": "shopify",
        "enabled": True,
    },

    # ================= WORKING HTML SCRAPES =================
    {
        "name": "Vijay Sales - PS5 search",
        "url": "https://www.vijaysales.com/search/playstation-5",
        "type": "html",
        "enabled": True,
    },
    {
        "name": "Flipkart - PS5 search",
        "url": "https://www.flipkart.com/search?q=playstation%205%20console",
        "type": "html",
        "enabled": True,
    },
    {
        # "no decisive signal" = this is a search page, and the add-to-cart
        # check only works on product pages. When a PS5 listing exists, open
        # it, copy the amazon.in/dp/XXXXXXXXXX URL, and paste it here. That
        # single change turns Amazon from a guess into a reliable check.
        "name": "Amazon.in - PS5 search",
        "url": "https://www.amazon.in/s?k=playstation+5+console&i=videogames",
        "type": "amazon",
        "enabled": True,
    },

    # ================= QUICK COMMERCE (all off -- see note) =================
    # Tested and all four failed:
    #   Blinkit   -> HTTP 403. Bot protection; a bare lat/lon header is not
    #                enough, their API wants a real app session token.
    #   Zepto     -> empty HTML shell. React SPA, products load after JS runs.
    #   Instamart -> same.
    #
    # These are not fixable by tweaking headers. Two real options:
    #   (a) Find the internal XHR endpoint in DevTools while logged in with
    #       your location set -- see "Reviving quick commerce" in DEPLOY.md.
    #   (b) Drive a headless browser (Playwright). Works, but ~15s per site
    #       and heavy for a free runner.
    #
    # Worth weighing: Sony's Blinkit rollout covered Delhi NCR, Mumbai and
    # Bengaluru. Hyderabad coverage is unconfirmed, so this may buy nothing.
    {
        "name": "Blinkit - PS5 search",
        "url": "https://blinkit.com/s/?q=playstation%205",
        "type": "html",
        "headers": QC_HEADERS,
        "enabled": False,
    },
    {
        "name": "Zepto - PS5 Slim console",
        "url": "https://www.zepto.com/pn/playstation-5-console-slim-playstation-5-console-e-chasis-slim/pvid/ad968d7d-c5d8-415e-b7d4-58f84ff13076",
        "type": "html",
        "headers": QC_HEADERS,
        "enabled": False,
    },
    {
        "name": "Zepto - PS5 search",
        "url": "https://www.zepto.com/search?query=playstation%205",
        "type": "html",
        "headers": QC_HEADERS,
        "enabled": False,
    },
    {
        "name": "Swiggy Instamart - PS5 search",
        "url": "https://www.swiggy.com/instamart/search?custom_back=true&query=playstation",
        "type": "html",
        "headers": QC_HEADERS,
        "enabled": False,
    },

    # ================= JS-RENDERED / BROKEN =================
    {
        # Also a JS shell -- returned "no PS5 mention on page".
        "name": "JioMart - PS5 search",
        "url": "https://www.jiomart.com/search/playstation%205",
        "type": "html",
        "enabled": False,
    },
    {
        # Both /search/ps5 and /Search/... now 404 -- the site changed its URL
        # scheme. Browse to a real PS5 listing, paste that URL here, re-enable.
        "name": "Games The Shop - PS5 search",
        "url": "https://www.gamestheshop.com/search/ps5",
        "type": "html",
        "enabled": False,
    },
    {
        "name": "Croma - PS5 search",
        "url": "https://www.croma.com/searchB?q=playstation%205%3Arelevance",
        "type": "html",
        "enabled": False,
    },
    {
        "name": "Reliance Digital - PS5 search",
        "url": "https://www.reliancedigital.in/search?q=playstation%205",
        "type": "html",
        "enabled": False,
    },
]

# ---------------------------------------------------------------- reddit
REDDIT_SUBS = ["PS5India", "IndianGaming", "playstation"]
REDDIT_KEYWORDS = [
    "restock", "in stock", "back in stock", "drop", "live now",
    "available now", "shopatsc", "blinkit", "zepto", "ps5 stock",
]
