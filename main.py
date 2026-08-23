#!/usr/bin/env python3
"""
PS5 stock tracker -> Telegram.

    python main.py --once      one sweep, then exit   (GitHub Actions / cron)
    python main.py             daemon loop            (VM / your own PC)
    python main.py --test      send a test message and dump current state
"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

import config
import checkers
import notify

STATE_FILE = os.environ.get("PS5_STATE_FILE", "state.json")
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist():
    return datetime.now(IST)


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"targets": {}, "reddit_seen": [], "last_heartbeat": 0}


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)


def should_alert(prev, result):
    """Alert on OUT/UNKNOWN/ERROR -> IN transitions, plus periodic re-alerts."""
    if result.status != checkers.IN:
        return False
    if prev is None:
        return True                      # first ever sighting, and it's in stock
    if prev.get("status") != checkers.IN:
        return True                      # the transition we care about
    if config.REPEAT_ALERT_MINUTES:
        age = time.time() - prev.get("last_alert", 0)
        return age > config.REPEAT_ALERT_MINUTES * 60
    return False


def format_alert(result):
    price = f"\n💰 {result.price}" if result.price else ""
    pins = " / ".join(config.PINCODES)
    return (
        f"🚨 <b>PS5 IN STOCK</b> 🚨\n\n"
        f"<b>{result.name}</b>{price}\n\n"
        f"👉 <a href=\"{result.url}\">OPEN NOW</a>\n\n"
        f"<i>Check delivery for {pins}. Go. Don't read this message.</i>"
    )


def sweep(state, verbose=True):
    """Run all checks once. Returns list of Results."""
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as pool:
        results = list(pool.map(checkers.check, checkers.active_targets()))

    alerts_sent = 0
    for r in results:
        key = r.name
        prev = state["targets"].get(key)

        if verbose:
            tag = {"IN_STOCK": "IN ", "OUT_OF_STOCK": "out",
                   "UNKNOWN": " ? ", "ERROR": "err"}.get(r.status, "   ")
            detail = r.note or r.evidence or ""
            print(f"  [{tag}] {r.name[:44]:<44} {r.price:>10} {detail[:40]}")

        if should_alert(prev, r):
            if notify.send(format_alert(r)):
                alerts_sent += 1
                state["targets"][key] = {"status": r.status,
                                         "last_alert": time.time(),
                                         "price": r.price}
                continue

        state["targets"][key] = {
            "status": r.status,
            "last_alert": (prev or {}).get("last_alert", 0),
            "price": r.price,
        }

    # ---- reddit early warning ----
    try:
        hits, seen = checkers.check_reddit(state.get("reddit_seen", []))
        state["reddit_seen"] = seen
        for h in hits[:4]:                       # cap so one busy hour can't spam
            notify.send(
                f"📣 <b>Restock chatter</b> — r/{h['sub']}\n\n"
                f"{h['title']}\n\n<a href=\"{h['url']}\">Read thread</a>",
                silent=True,
            )
            alerts_sent += 1
    except Exception as e:
        if verbose:
            print(f"  [err] reddit: {e}")

    return results, alerts_sent


def maybe_heartbeat(state, results):
    if not config.HEARTBEAT_HOURS:
        return
    if time.time() - state.get("last_heartbeat", 0) < config.HEARTBEAT_HOURS * 3600:
        return
    ok = sum(1 for r in results if r.status in (checkers.IN, checkers.OUT))
    err = sum(1 for r in results if r.status == checkers.ERROR)
    notify.send(
        f"✅ Tracker alive — {now_ist():%d %b, %I:%M %p} IST\n"
        f"{ok}/{len(results)} sites reading cleanly, {err} erroring.\n"
        f"No stock yet.",
        silent=True,
    )
    state["last_heartbeat"] = time.time()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="single sweep then exit")
    ap.add_argument("--test", action="store_true", help="send test message")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.test:
        print("curl_cffi:", "yes" if checkers.HAS_CFFI else "NO (install it)")
        notify.send("🧪 PS5 tracker test — delivery is working.")
        results, _ = sweep(load_state(), verbose=True)
        return

    state = load_state()

    if args.once:
        print(f"--- sweep {now_ist():%Y-%m-%d %H:%M:%S} IST ---")
        results, sent = sweep(state, verbose=not args.quiet)
        maybe_heartbeat(state, results)
        save_state(state)
        print(f"--- {sent} alert(s) sent ---")
        return

    notify.send("🟢 PS5 tracker started. Watching "
                f"{len(config.TARGETS)} sites every ~{config.POLL_SECONDS}s.",
                silent=True)
    while True:
        try:
            print(f"--- sweep {now_ist():%H:%M:%S} IST ---")
            results, sent = sweep(state, verbose=not args.quiet)
            maybe_heartbeat(state, results)
            save_state(state)
        except KeyboardInterrupt:
            notify.send("🔴 PS5 tracker stopped.", silent=True)
            sys.exit(0)
        except Exception as e:
            print(f"sweep failed: {e}", file=sys.stderr)

        delay = config.POLL_SECONDS + random.uniform(
            -config.JITTER_SECONDS, config.JITTER_SECONDS)
        time.sleep(max(10, delay))


if __name__ == "__main__":
    main()
