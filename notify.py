"""
Telegram delivery. Raw HTTP -- no bot library needed.

Credentials are read from, in order:
    1. environment variables  (TG_BOT_TOKEN / TG_CHAT_ID)  <- used by CI/systemd
    2. a local .env file next to this script                <- used on your laptop

The .env file is why you no longer have to `export` in every new terminal.
It is gitignored and never leaves your machine.

    python notify.py --whoami    find your chat ID
    python notify.py --check     verify credentials are loaded
"""

import os
import sys
import json
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{}/{}"
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def _load_env_file(path=ENV_PATH):
    """Minimal .env parser. Real env vars always win, so CI is unaffected."""
    if not os.path.exists(path):
        return
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        print(f"[notify] could not read .env: {e}", file=sys.stderr)


_load_env_file()

TOKEN = os.environ.get("TG_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TG_CHAT_ID", "").strip()


def _call(method, params):
    if not TOKEN:
        raise RuntimeError("TG_BOT_TOKEN is not set (env var or .env file)")
    url = API.format(TOKEN, method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def credentials_ok():
    """True if both values are present. Used for the startup guard."""
    return bool(TOKEN and CHAT_ID)


def missing():
    out = []
    if not TOKEN:
        out.append("TG_BOT_TOKEN")
    if not CHAT_ID:
        out.append("TG_CHAT_ID")
    return out


def send(text, silent=False):
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
    try:
        res = _call("getUpdates", {})
    except Exception as e:
        print(f"Could not reach Telegram: {e}")
        return
    updates = res.get("result", [])
    if not updates:
        print("No updates. Open your bot in Telegram, press Start, send 'hi',")
        print("then run this again.")
        return
    seen = {}
    for u in updates:
        msg = u.get("message") or u.get("channel_post") or {}
        chat = msg.get("chat", {})
        if chat.get("id"):
            seen[chat["id"]] = (chat.get("username") or chat.get("title")
                                or chat.get("first_name"))
    print("Add this line to your .env file:\n")
    for cid, who in seen.items():
        print(f"TG_CHAT_ID={cid}          # {who}")


def check():
    print(f".env path : {ENV_PATH}")
    print(f".env found: {'yes' if os.path.exists(ENV_PATH) else 'NO'}")
    print(f"token     : {'set (' + TOKEN[:8] + '...)' if TOKEN else 'MISSING'}")
    print(f"chat id   : {CHAT_ID if CHAT_ID else 'MISSING'}")
    if credentials_ok():
        print("\nSending test message...")
        print("delivered" if send("Credentials check - delivery works.")
              else "FAILED")
    else:
        print(f"\nMissing: {', '.join(missing())}")


if __name__ == "__main__":
    if "--whoami" in sys.argv:
        whoami()
    elif "--check" in sys.argv:
        check()
    else:
        print("sent" if send("PS5 tracker: test message.") else "not sent")
