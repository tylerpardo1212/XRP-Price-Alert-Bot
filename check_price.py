"""
XRP Price Alert Bot
Watches XRP's price against your grid bot's upper and lower limits, and
texts you when price gets close to either edge, since that's when your
bot is at risk of going idle and might need its range adjusted.

Designed to run on a schedule via GitHub Actions (see .github/workflows/check.yml).
State (last alert sent) is persisted to state.json and committed back to the repo
so the bot doesn't spam you every run once a threshold is crossed.
"""

import os
import json
import sys
from datetime import datetime, timezone
import urllib.request
import urllib.error
import urllib.parse
import base64

# ---------- SETTINGS: edit these to match your grid bot ----------
LOWER_LIMIT = 1.134            # your bot's lower limit (USD)
UPPER_LIMIT = 1.164            # your bot's upper limit (USD)
BUFFER_PCT = 0.25             # alert when price is within this % of the range from either edge
COOLDOWN_HOURS = .5          # don't re-alert for the same edge within this many hours
# --------------------------------------------------------------------

STATE_FILE = "state.json"
COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=ripple&vs_currencies=usd"
)


def get_xrp_price():
    """Fetch current XRP price from CoinGecko (free, no API key needed)."""
    req = urllib.request.Request(COINGECKO_URL, headers={"User-Agent": "xrp-alert-bot"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    return data["ripple"]["usd"]


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_alert_direction": None, "last_alert_time": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def hours_since(iso_timestamp):
    if not iso_timestamp:
        return None
    then = datetime.fromisoformat(iso_timestamp)
    now = datetime.now(timezone.utc)
    return (now - then).total_seconds() / 3600.0


def send_call(message):
    """Place a phone call via Twilio that reads the alert message aloud.
    Requires TWILIO_SID, TWILIO_AUTH, TWILIO_FROM, TWILIO_TO to be set as
    environment variables (GitHub Actions secrets). Uses inline TwiML so no
    separate webhook/server is needed."""
    import xml.sax.saxutils as xss

    sid = os.environ["TWILIO_SID"]
    auth = os.environ["TWILIO_AUTH"]
    from_number = os.environ["TWILIO_FROM"]
    to_number = os.environ["TWILIO_TO"]

    safe_message = xss.escape(message)
    # Say it twice so it's easier to catch on a phone call
    twiml = (
        f'<Response>'
        f'<Say voice="Polly.Joanna">{safe_message}</Say>'
        f'<Pause length="1"/>'
        f'<Say voice="Polly.Joanna">Repeating. {safe_message}</Say>'
        f'</Response>'
    )

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
    payload = urllib.parse.urlencode({
        "To": to_number,
        "From": from_number,
        "Twiml": twiml,
    }).encode()

    creds = base64.b64encode(f"{sid}:{auth}".encode()).decode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Basic {creds}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print("Twilio response:", resp.status)
    except urllib.error.HTTPError as e:
        print("Twilio error:", e.read().decode())
        raise


def main():
    price = get_xrp_price()
    range_width = UPPER_LIMIT - LOWER_LIMIT
    buffer_zone = range_width * (BUFFER_PCT / 100)

    lower_alert_line = LOWER_LIMIT + buffer_zone
    upper_alert_line = UPPER_LIMIT - buffer_zone

    print(f"XRP price: ${price:.4f}  |  Range: ${LOWER_LIMIT:.4f}-${UPPER_LIMIT:.4f}  |  "
          f"Alert zone: below ${lower_alert_line:.4f} or above ${upper_alert_line:.4f}")

    edge = None
    if price <= lower_alert_line:
        edge = "lower"
    elif price >= upper_alert_line:
        edge = "upper"

    if edge is None:
        print("No alert. Price is comfortably inside the range.")
        return

    state = load_state()
    hrs_since_last = hours_since(state.get("last_alert_time"))
    same_edge_recent = (
        state.get("last_alert_direction") == edge
        and hrs_since_last is not None
        and hrs_since_last < COOLDOWN_HOURS
    )

    if same_edge_recent:
        print(f"Price is near the {edge} limit but still in cooldown "
              f"({hrs_since_last:.1f}h since last {edge} alert). Skipping.")
        return

    if edge == "lower":
        message = (
            f"XRP ALERT: price ${price:.4f} is nearing your LOWER limit (${LOWER_LIMIT:.4f}). "
            f"Might be time to check your bot's range."
        )
    else:
        message = (
            f"XRP ALERT: price ${price:.4f} is nearing your UPPER limit (${UPPER_LIMIT:.4f}). "
            f"Might be time to check your bot's range."
        )
    print("Sending alert:", message)

    # In dry-run mode (no Twilio secrets set), just print instead of calling
    if "TWILIO_SID" in os.environ:
        send_call(message)
    else:
        print("[DRY RUN] Twilio secrets not set, skipping actual call.")

    state["last_alert_direction"] = edge
    state["last_alert_time"] = datetime.now(timezone.utc).isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
