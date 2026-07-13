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

## Adjusting the threshold

Open `check_price.py` and change these two lines near the top:

```python
THRESHOLD_PCT = 5.0          # alert if 24hr change exceeds +/- this %
COOLDOWN_HOURS = 6           # don't re-alert same direction within this many hours
```

The cooldown exists so that if XRP is up 6% and stays up 6% for the next
three checks, you get one text, not twelve.

## Upgrading to phone calls later

When you're ready to switch from text to an actual call, Twilio's Voice API
uses the same account and credentials you already have. It's a small code
change in `send_sms()` (swap the Messages endpoint for the Calls endpoint
with a short TwiML script to read out the alert). Just let me know when
you're ready and I'll make that change.

## A couple of honest caveats

- CoinGecko's free API updates on a short delay (not tick-by-tick), which is
  fine for a 5% daily-move alert but don't expect second-by-second precision.
- GitHub's cron schedule is "best effort," meaning under heavy platform load
  a run might fire a few minutes late. Not an issue for a 24hr threshold.
