# PS5 Stock Tracker → Telegram

Polls Indian retailers for PlayStation 5 stock and pings your Telegram the moment
something flips from out-of-stock to in-stock. Free to run.

Configured for pincodes **500085 / 500072** (Kukatpally / Nizampet, Hyderabad).

---

## 0. Revoke your old token first

If you ever pasted your bot token into a chat, an email, or a public repo, it's
burned. Open [@BotFather](https://t.me/BotFather) → `/mybots` → your bot →
**API Token** → **Revoke current token**. Use the new one below.

Never commit the token. This project reads it from the environment only.

---

## 1. Local setup (5 minutes)

```bash
pip install -r requirements.txt

export TG_BOT_TOKEN="your-new-token-from-botfather"
```

Now open your bot in Telegram, press **Start**, send it any message, then:

```bash
python notify.py --whoami
# prints: TG_CHAT_ID=123456789   (yourname)

export TG_CHAT_ID="123456789"
python main.py --test
```

You should get a test message and a table of every site's current status.

**Windows PowerShell:** use `$env:TG_BOT_TOKEN="..."` instead of `export`.

---

## 2. Pick where it runs

| Option | Cost | Check interval | Verdict |
|---|---|---|---|
| **Oracle Cloud Always Free VM** | ₹0 forever | 45 sec | Best. Real 24/7 box, ARM Ampere, no time limit |
| **Your own PC** | ₹0 | 45 sec | Fine while it's on. Won't catch a 3 AM drop |
| **GitHub Actions** | ₹0 | 5 min (often 10–15) | Zero setup, but too slow for fast drops |
| Render / Railway free | ₹0 | varies | Free tiers sleep — instances get killed |

### Oracle Cloud (recommended)

Sign up for Always Free, create an Ampere A1 instance (Ubuntu), SSH in:

```bash
sudo apt update && sudo apt install -y python3-pip git
git clone <your-repo> ps5-tracker && cd ps5-tracker
pip3 install -r requirements.txt
```

Run it as a service so it survives reboots:

```bash
sudo tee /etc/systemd/system/ps5.service > /dev/null << 'EOF'
[Unit]
Description=PS5 stock tracker
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ps5-tracker
Environment="TG_BOT_TOKEN=PASTE_TOKEN_HERE"
Environment="TG_CHAT_ID=PASTE_CHAT_ID_HERE"
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ps5
journalctl -u ps5 -f          # watch it work
```

### GitHub Actions

Push this repo (private is fine), then **Settings → Secrets and variables →
Actions → New repository secret**:

- `TG_BOT_TOKEN`
- `TG_CHAT_ID`

The workflow in `.github/workflows/ps5.yml` runs every 5 minutes and commits
`state.json` back so it remembers what it already alerted on.

Cron on free runners is best-effort — 5-minute schedules frequently land 10–15
minutes late during busy periods. Use it as a safety net, not your primary.

---

## 3. Finding the right URLs

The search URLs in `config.py` work, but **direct product URLs are far more
reliable** than search pages. Once a PS5 listing exists, grab its real URL and
replace the search URL in `config.py`.

For Amazon specifically, use the product page (`amazon.in/dp/ASIN`), not a
search URL — the `add-to-cart-button` check only works on product pages and is
the single most reliable signal in this whole project.

### Adding a JSON endpoint (best accuracy)

Many of these sites load stock over an internal API. To find it:

1. Open the product page in Chrome → **F12** → **Network** tab → filter **Fetch/XHR**
2. Reload the page
3. Look for a response containing the price or a `stock` / `inventory` field
4. Right-click → **Copy link address**

Add it to `config.py`:

```python
{
    "name": "Croma - PS5 (API)",
    "url": "https://api.croma.com/...paste-here...",
    "type": "json",
    "tier": 1,
},
```

You may need to adjust the flag names in `check_json()` in `checkers.py` to
match what that particular API returns.

### Tuning signals per site

If a site gives false readings, override its keywords:

```python
{
    "name": "Vijay Sales - PS5",
    "url": "...",
    "type": "html",
    "out_signals": ["sold out", "notify me"],   # only these count as OUT
    "in_signals": ["add to cart"],
},
```

---

## 4. What actually works, honestly

**Reliable:** ShopAtSC, Games The Shop, Vijay Sales, Croma, Reliance Digital,
JioMart. Straightforward sites, minimal bot protection. These are also where
Sony restocks land first — ShopAtSC in particular.

**Unreliable:** Amazon and Flipkart run serious bot detection. `curl_cffi`
impersonates a real Chrome TLS fingerprint, which gets you a long way, but
you'll still see periodic `blocked (HTTP 503)` errors. That's expected, not a
bug. If Amazon matters most to you, the sturdier path is Amazon's own
[Product Advertising API](https://webservices.amazon.in/paapi5/documentation/)
— though it requires an affiliate account with qualifying sales.

**Skip the quick-commerce apps.** Blinkit, Zepto and Instamart don't carry
₹50,000 consoles — they're groceries and convenience SKUs. Their APIs also
require per-device auth tokens that rotate. `PINCODE_COORDS` is in the config if
you want to experiment, but it isn't wired up, and I'd spend the effort
elsewhere.

**The Reddit monitor may be your best feature.** r/PS5India users consistently
post restock news before listings go live, and it costs one free API call. On a
5-minute polling schedule, human tip-offs will beat your own scraper more often
than not.

---

## 5. Setting expectations

Indian PS5 restocks since the April 2026 price hike have been drop events that
clear in minutes, sometimes seconds. A 45-second poller gives you a real shot.
A 5-minute one gives you a partial one. Neither beats someone sitting on the
page with a card already saved.

So stack the deck:

- **Save your address and card** on ShopAtSC, Croma, Vijay Sales and Amazon *now*, before a drop
- **Turn off Telegram's silent notifications** for this bot, and set the chat to a loud custom tone
- **Add ShopAtSC to your Telegram alerts and check it manually** during sale events — it's Sony's own channel and often first
- Sale windows (Prime Day, Great Indian Festival, Croma/Vijay Sales sale days) are when stock actually appears — be at your desk

Also: don't buy from a reseller quoting ₹65,000+. Every restock cycle produces
grey-market listings with no Sony India warranty. The whole point of this bot
is to not need them.

---

## 6. Being a good citizen

`POLL_SECONDS = 45` across ~8 sites is roughly one request per site per minute.
That's polite and won't get you banned. If you drop it to 5 seconds you will get
IP-blocked, your checks will start failing, and you'll miss the drop you built
this for. Slower and working beats faster and blocked.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `TG_BOT_TOKEN is not set` | Export the env var in the same shell you run from |
| `--whoami` prints nothing | Message the bot first, press Start, then re-run |
| Everything says `blocked` | Install `curl_cffi` — it's doing the heavy lifting |
| Amazon always errors | Normal. Use a `/dp/ASIN` product URL, not search |
| No alerts ever | Run `--test`; if sites show `out`, the bot is working and there's genuinely no stock |
| Repeated alerts | Raise `REPEAT_ALERT_MINUTES` in `config.py`, or set it to `0` |
| Alerts for the wrong thing | The page had "add to cart" for an accessory. Use a direct product URL |
