# XRP Price Alert Bot

Checks XRP's 24hr price change every 15 minutes and texts you when it moves
more than a threshold you set (default: 5%). Runs entirely on GitHub's free
servers, nothing needs to stay on at your end.

## What it costs

- GitHub Actions: free for a repo this small (public repos have generous free
  minutes; private repos also get a free monthly allowance that this easily
  fits under).
- Twilio: free trial credit covers a good number of texts (and calls, later)
  to your own verified number. After the trial credit runs out, texts are a
  fraction of a cent each.

## One-time setup

### 1. Twilio account
1. Sign up at twilio.com (free trial).
2. From the Twilio Console dashboard, copy your **Account SID** and **Auth
   Token**.
3. Get a free trial phone number (Twilio assigns you one).
4. Under "Verified Caller IDs," verify your own cell number. Trial accounts
   can only text/call numbers you've verified.

### 2. Create a GitHub repo
1. Create a new **private** repo (e.g. `xrp-alert-bot`).
2. Upload these three files, keeping the folder structure:
   - `check_price.py`
   - `.github/workflows/check.yml`
   - `state.json` (starter file, included)

### 3. Add your secrets
In the repo: **Settings -> Secrets and variables -> Actions -> New repository
secret**. Add these four:

| Secret name    | Value                                  |
|----------------|-----------------------------------------|
| `TWILIO_SID`   | Your Account SID                        |
| `TWILIO_AUTH`  | Your Auth Token                         |
| `TWILIO_FROM`  | Your Twilio trial phone number          |
| `TWILIO_TO`    | Your own verified cell number           |

Use full international format for phone numbers, e.g. `+13135551234`.

### 4. Test it
Go to the **Actions** tab, select "XRP Price Check," and click **Run
workflow** to trigger it manually. Check the log output to confirm it's
reading the price correctly. If your secrets aren't set yet, it runs in
"dry run" mode and just prints what it would have sent, so it's safe to test
before Twilio is wired up.

Once secrets are set and the schedule kicks in, it checks automatically
every 15 minutes.

## How the alert works

Instead of tracking daily price swings, this watches your actual grid bot's
range and texts you when price is getting close to either edge, since that's
the point where your bot is at risk of going idle (fully sold out of XRP if
price breaks the ceiling, or fully out of USD if it breaks the floor).

Open `check_price.py` and edit these near the top any time you adjust your
bot's parameters on Webot:

```python
LOWER_LIMIT = 0.915           # your bot's lower limit (USD)
UPPER_LIMIT = 1.356           # your bot's upper limit (USD)
BUFFER_PCT = 10.0             # alert when price is within this % of the range from either edge
COOLDOWN_HOURS = 12           # don't re-alert for the same edge within this many hours
```

With these numbers, you'll get a text if price drops to about $0.959 or
climbs to about $1.312, both 10% of the range's width away from the actual
edges, giving you a heads up before your bot actually stops working, not
after. The cooldown keeps it from texting you every 15 minutes while price
sits right at that line.

**Remember**: since the range is hardcoded, you need to update these two
numbers in this file (and commit the change) any time you actually change
your bot's upper/lower limit on Webot, or the alert will be watching the
wrong numbers.

## How you're alerted

This calls your phone and reads the alert message aloud (twice, for
clarity), rather than texting. Phone calls don't require the SMS carrier
registration process (A2P 10DLC) that texting does, so this was the faster
path to a fully working alert.

## A couple of honest caveats

- CoinGecko's free API updates on a short delay (not tick-by-tick), which is
  fine for a 5% daily-move alert but don't expect second-by-second precision.
- GitHub's cron schedule is "best effort," meaning under heavy platform load
  a run might fire a few minutes late. Not an issue for a 24hr threshold.
