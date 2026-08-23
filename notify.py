"""
Telegram delivery. Raw HTTP -- no bot library needed.

Set two environment variables:
    TG_BOT_TOKEN   from @BotFather
    TG_CHAT_ID     run `python notify.py --whoami` after messaging your bot
"""

import os
import sys
import json
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TG_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TG_CHAT_ID", "").strip()
API = "https://api.telegram.org/bot{}/{}"


def _call(method, params):
    if not TOKEN:
        raise RuntimeError("TG_BOT_TOKEN is not set")
    url = API.format(TOKEN, method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def send(text, silent=False):
    """Send a message. Returns True on success, never raises on network trouble."""
    if not CHAT_ID:
        print("[notify] TG_CHAT_ID not set -- printing instead:\n" + text)
        return False
    try:
        _call("sendMessage", {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
            "disable_notification": "true" if silent else "false",
        })
        return True
    except Exception as e:
        print(f"[notify] send failed: {e}", file=sys.stderr)
        return False


def whoami():
    """Print chat IDs that have messaged this bot."""
    try:
        res = _call("getUpdates", {})
    except Exception as e:
        print(f"Could not reach Telegram: {e}")
        return
    updates = res.get("result", [])
    if not updates:
        print("No updates. Open your bot in Telegram, press Start, send 'hi', then re-run.")
        return
    seen = {}
    for u in updates:
        msg = u.get("message") or u.get("channel_post") or {}
        chat = msg.get("chat", {})
        if chat.get("id"):
            seen[chat["id"]] = chat.get("username") or chat.get("title") or chat.get("first_name")
    for cid, who in seen.items():
        print(f"TG_CHAT_ID={cid}   ({who})")


if __name__ == "__main__":
    if "--whoami" in sys.argv:
        whoami()
    else:
        ok = send("PS5 tracker: test message. If you see this, delivery works.")
        print("sent" if ok else "not sent")
