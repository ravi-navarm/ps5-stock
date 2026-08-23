# Fix: alerts printing to terminal instead of Telegram

`TG_CHAT_ID not set` means the bot found a restock-worthy state but had
nowhere to send it. Fix it once with a `.env` file.

## On your Mac

```bash
cd ~/Desktop/ps5-tracker
cp .env.example .env
nano .env
```

Fill in both lines, no quotes needed:

```
TG_BOT_TOKEN=8123456789:AAG...your-real-token
TG_CHAT_ID=987654321
```

Ctrl+O, Enter, Ctrl+X to save.

Don't have the chat ID? Message your bot in Telegram (press Start, send "hi"),
then:

```bash
python notify.py --whoami
```

It prints the exact line to paste into `.env`.

Verify:

```bash
python notify.py --check
```

You want `.env found: yes`, both values set, and a message on your phone.
Now every new terminal works with no `export`.

## On GitHub Actions

Nothing changes. Real environment variables take precedence over `.env`, so
repository Secrets still win. `.env` is gitignored and never pushed.

## Reviving quick commerce (optional)

Blinkit returns 403 and Zepto/Instamart are React apps that render after JS,
so plain fetches see nothing. Neither is fixable with headers.

If you want them, find the real endpoint yourself:

1. Open the site in Chrome, set your delivery location to 500085
2. F12 -> **Network** -> filter **Fetch/XHR**
3. Search for "playstation"
4. Find the response containing product names and prices
5. Right-click -> Copy -> **Copy as cURL**

Send me that cURL and I'll wire it up. It carries your session headers, which
is exactly what the 403 is asking for.

Weigh it first: Sony's Blinkit rollout covered Delhi NCR, Mumbai and
Bengaluru. Hyderabad coverage is unconfirmed, so this may buy you nothing.
