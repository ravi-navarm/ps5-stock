"""
Stock checkers.  (v2)

New: check_shopify() reads Shopify's public products.json, which reports
per-variant availability as a boolean. No keyword guessing, no bot walls.
This is how the ShopAtSC checks work now.
"""

import re
import json
import html as htmllib
import random
from dataclasses import dataclass

import config

try:
    from curl_cffi import requests as http
    HAS_CFFI = True
except ImportError:
    import requests as http
    HAS_CFFI = False

IMPERSONATIONS = ["chrome124", "chrome123", "chrome120", "edge101"]

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en-GB;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

FALLBACK_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

IN, OUT, UNKNOWN, ERROR = "IN_STOCK", "OUT_OF_STOCK", "UNKNOWN", "ERROR"


@dataclass
class Result:
    name: str
    url: str
    status: str
    price: str = ""
    note: str = ""
    evidence: str = ""


# ------------------------------------------------------------------ fetching

def fetch(url, extra_headers=None, timeout=None):
    headers = dict(BASE_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    timeout = timeout or config.REQUEST_TIMEOUT

    kwargs = {"headers": headers, "timeout": timeout}
    if HAS_CFFI:
        kwargs["impersonate"] = random.choice(IMPERSONATIONS)
    else:
        headers["User-Agent"] = FALLBACK_UA

    r = http.get(url, **kwargs)
    if r.status_code in (403, 429, 503):
        raise RuntimeError(f"blocked (HTTP {r.status_code})")
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}")
    return r.text


def normalize(raw):
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", raw)
    text = htmllib.unescape(text)
    return re.sub(r"\s+", " ", text).lower()


PRICE_RE = re.compile(r"(?:₹|rs\.?\s?|inr\s?)\s?([\d][\d,]{3,8})")


def extract_price(text):
    """Lowest price in console range. Floor is high enough to skip accessories."""
    vals = []
    for m in PRICE_RE.finditer(text):
        try:
            v = int(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if config.PRICE_FLOOR <= v <= config.PRICE_CEILING:
            vals.append(v)
    return f"₹{min(vals):,}" if vals else ""


def is_console(title):
    """
    True only if a title names an actual console.

    Requires a positive marker (console / chassis / digital edition) AND no
    accessory word. Word boundaries matter: "PS5 Standard E Chassis" must not
    trip on "stand", and "PS5 Returnal" is a game, not hardware.
    """
    t = title.lower()
    if not ("ps5" in t or "playstation 5" in t or "playstation®5" in t
            or "playstation®5" in t):
        return False

    if not any(re.search(r"\b" + re.escape(p), t) for p in config.CONSOLE_MARKERS):
        return False

    # Plural-aware: "Console Covers" must match the "cover" exclusion.
    return not any(re.search(r"\b" + re.escape(b) + r"s?\b", t)
                   for b in config.NOT_A_CONSOLE)


# ------------------------------------------------------------------ shopify

def check_shopify(target):
    """
    Read Shopify's public products.json. Every Shopify store exposes this at
    /collections/<handle>/products.json and each variant carries a boolean
    `available` field -- ground truth, no keyword matching required.
    """
    name = target["name"]
    link = target.get("link", target["url"])
    try:
        raw = fetch(target["url"], extra_headers={"Accept": "application/json"})
        data = json.loads(raw)
    except json.JSONDecodeError:
        return Result(name, link, ERROR, note="not JSON (endpoint may be disabled)")
    except Exception as e:
        return Result(name, link, ERROR, note=str(e))

    products = data.get("products", [])
    if not products:
        return Result(name, link, UNKNOWN, note="collection empty")

    consoles, available = 0, []
    for p in products:
        title = p.get("title", "")
        if not is_console(title):
            continue
        consoles += 1
        for v in p.get("variants", []):
            if v.get("available"):
                try:
                    price = int(float(v.get("price", 0)))
                except (TypeError, ValueError):
                    price = 0
                # Second line of defence: nothing under the floor is a console,
                # whatever its title claims. Catches accessories that slip the
                # keyword filter.
                if price and price < config.PRICE_FLOOR:
                    continue
                available.append((title, price, p.get("handle", "")))

    if available:
        title, price, handle = available[0]
        product_url = f"https://shopatsc.com/products/{handle}" if handle else link
        return Result(name, product_url, IN,
                      price=f"₹{price:,}" if price else "",
                      evidence=f"{title[:50]} (+{len(available)-1} more)"
                               if len(available) > 1 else title[:60])

    if consoles:
        return Result(name, link, OUT, evidence=f"{consoles} console(s), none available")
    return Result(name, link, UNKNOWN, note=f"{len(products)} products, no console matched")


# ------------------------------------------------------------------ html

def check_html(target):
    name, url = target["name"], target["url"]
    try:
        raw = fetch(url, extra_headers=target.get("headers"))
    except Exception as e:
        return Result(name, url, ERROR, note=str(e))

    text = normalize(raw)

    if len(text) < 500:
        return Result(name, url, ERROR, note="JS-rendered or blocked")
    if "playstation" not in text and "ps5" not in text:
        return Result(name, url, UNKNOWN, note="no PS5 mention on page")

    out_hits = [s for s in target.get("out_signals", config.OUT_SIGNALS) if s in text]
    if out_hits:
        return Result(name, url, OUT, price=extract_price(text), evidence=out_hits[0])

    in_hits = [s for s in target.get("in_signals", config.IN_SIGNALS) if s in text]
    if in_hits:
        return Result(name, url, IN, price=extract_price(text), evidence=in_hits[0])

    return Result(name, url, UNKNOWN, note="no clear signal")


def check_amazon(target):
    name, url = target["name"], target["url"]
    try:
        raw = fetch(url, extra_headers={"Referer": "https://www.amazon.in/"})
    except Exception as e:
        return Result(name, url, ERROR, note=str(e))

    low = raw.lower()
    if "api-services-support@amazon.com" in low or "to discuss automated access" in low:
        return Result(name, url, ERROR, note="Amazon bot wall")

    if 'id="add-to-cart-button"' in low or "add-to-cart-button" in low:
        return Result(name, url, IN, price=extract_price(normalize(raw)),
                      evidence="add-to-cart-button present")

    if "currently unavailable" in low or "out of stock" in low:
        return Result(name, url, OUT, evidence="unavailable text")

    if "/s?k=" in url or "/s/" in url:
        text = normalize(raw)
        if "playstation" in text and "currently unavailable" not in text:
            return Result(name, url, UNKNOWN, note="search page, open to verify")

    return Result(name, url, UNKNOWN, note="no decisive signal")


HANDLERS = {
    "html": check_html,
    "amazon": check_amazon,
    "shopify": check_shopify,
}


def check(target):
    handler = HANDLERS.get(target.get("type", "html"), check_html)
    try:
        return handler(target)
    except Exception as e:
        return Result(target["name"], target.get("link", target["url"]),
                      ERROR, note=f"handler crash: {e}")


def active_targets():
    """Only targets not explicitly disabled."""
    return [t for t in config.TARGETS if t.get("enabled", True)]


# ------------------------------------------------------------------ reddit

def check_reddit(seen_ids):
    hits = []
    seen = set(seen_ids)
    for sub in config.REDDIT_SUBS:
        url = f"https://www.reddit.com/r/{sub}/new.json?limit=25"
        try:
            raw = fetch(url, extra_headers={
                "Accept": "application/json",
                "User-Agent": "ps5-tracker/1.0 (personal restock alerts)",
            })
            data = json.loads(raw)
        except Exception:
            continue

        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            pid = post.get("id")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            title = post.get("title") or ""
            blob = (title + " " + (post.get("selftext") or "")).lower()
            if "ps5" not in blob and "playstation" not in blob:
                continue
            if any(k in blob for k in config.REDDIT_KEYWORDS):
                hits.append({
                    "sub": sub,
                    "title": title,
                    "url": "https://reddit.com" + post.get("permalink", ""),
                })

    return hits, list(seen)[-800:]
