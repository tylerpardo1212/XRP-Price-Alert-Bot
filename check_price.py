"""
XRP Price Alert Bot
Checks XRP's 24hr price change and sends a text (or call, later) via Twilio
when it crosses a threshold you set below.

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

# ---------- SETTINGS: edit these ----------
THRESHOLD_PCT = 5.0          # alert if 24hr change exceeds +/- this %
COOLDOWN_HOURS = 6           # don't re-alert for the same direction within this many hours
# --------------------------------------------

STATE_FILE = "state.json"
COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=ripple&vs_currencies=usd&include_24hr_change=true"
)


def get_xrp_change():
    """Fetch current price and 24hr % change from CoinGecko (free, no API key needed)."""
    req = urllib.request.Request(COINGECKO_URL, headers={"User-Agent": "xrp-alert-bot"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    price = data["ripple"]["usd"]
    change_pct = data["ripple"]["usd_24h_change"]
    return price, change_pct


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


def send_sms(message):
    """Send an SMS via Twilio. Requires TWILIO_SID, TWILIO_AUTH, TWILIO_FROM, TWILIO_TO
    to be set as environment variables (GitHub Actions secrets)."""
    import base64

    sid = os.environ["TWILIO_SID"]
    auth = os.environ["TWILIO_AUTH"]
    from_number = os.environ["TWILIO_FROM"]
    to_number = os.environ["TWILIO_TO"]

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    payload = urllib.parse.urlencode({
        "To": to_number,
        "From": from_number,
        "Body": message,
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
    price, change_pct = get_xrp_change()
    print(f"XRP price: ${price:.4f}  |  24hr change: {change_pct:.2f}%")

    direction = "up" if change_pct > 0 else "down"
    state = load_state()

    crossed = abs(change_pct) >= THRESHOLD_PCT
    if not crossed:
        print(f"No alert. |{change_pct:.2f}%| is under the {THRESHOLD_PCT}% threshold.")
        return

    hrs_since_last = hours_since(state.get("last_alert_time"))
    same_direction_recent = (
        state.get("last_alert_direction") == direction
        and hrs_since_last is not None
        and hrs_since_last < COOLDOWN_HOURS
    )

    if same_direction_recent:
        print(f"Threshold crossed ({direction}) but still in cooldown "
              f"({hrs_since_last:.1f}h since last {direction} alert). Skipping.")
        return

    message = (
        f"XRP ALERT: {direction.upper()} {abs(change_pct):.2f}% in 24hr. "
        f"Current price: ${price:.4f}"
    )
    print("Sending alert:", message)

    # In dry-run mode (no Twilio secrets set), just print instead of sending
    if "TWILIO_SID" in os.environ:
        send_sms(message)
    else:
        print("[DRY RUN] Twilio secrets not set, skipping actual send.")

    state["last_alert_direction"] = direction
    state["last_alert_time"] = datetime.now(timezone.utc).isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
