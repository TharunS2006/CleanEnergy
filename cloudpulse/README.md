# CloudPulse

CloudPulse is a cloud cost monitoring and optimisation platform. Most cost tools stop at a dashboard: they show you a number and leave the rest to a human. CloudPulse carries every cost problem all the way through a loop:

**Signal → Context → Finding → Ownership → Action → Verification**

The unit of the product is the **decision-ready finding**: one problem, priced, explained, scored against every other problem, given an owner, tracked while it's being fixed, and then **checked against the next bill**. A saving only counts once the money actually leaves the bill.

| Stage | What CloudPulse does |
|---|---|
| **Signal** | Reads the bill, the resource inventory, VM metrics, Azure Advisor and the activity log on every sync |
| **Context** | Prices each signal per month from the *actual billed cost* where it has it, list prices otherwise |
| **Finding** | Turns it into one de-duplicated task with a priority score (P1–P4), severity, confidence and the evidence behind it |
| **Ownership** | Finds who created the resource from the audit log (tags second), matches them to a CloudPulse user and assigns it |
| **Action** | Assign, start, fix, dismiss with a reason, snooze, comment — with in-app notifications and a full history |
| **Verification** | Confirms the problem is gone, then compares 7 days of billed cost before and after, and records the real saving |

If a fixed thing comes back, the finding reopens and its saving is withdrawn. That's the part almost no tool in this space does.

CloudPulse only reads your cloud. It never changes or deletes anything in a cloud account.

---

## 1. Who signs in

| Account | Who it's for | What they can do |
|---|---|---|
| **Administrator** | You, the CloudPulse owner | Sees every workspace. Creates workspaces, connects clouds, adds people, resets passwords |
| **Demo** | Faculty and visitors | The **Explore the demo** button on the sign-in page, no password. Read-only, using sample data |
| **Customer: owner** | The organisation being monitored | Sees only their own workspace. Can sync, set budgets and import bills |
| **Customer: viewer** | Others in that organisation | Sees only their own workspace. Can look, not change |

A **workspace** holds one organisation's cloud connections and data. People only ever see the workspaces they belong to.

Your Azure (Microsoft) login is *not* a CloudPulse login. CloudPulse reaches your subscription with its own read-only identity. You then create a CloudPulse account for anyone who should see that workspace.

How passwords work:

- Passwords are stored hashed (scrypt), and sign-in attempts are rate-limited.
- Sessions live on the server and end after 12 hours.
- People the administrator adds get a temporary password and must choose their own at first sign-in.
- Stored cloud secrets are encrypted.

---

## 2. Run it on your laptop

You need Python 3.10 or newer.

**Windows (Command Prompt)**
```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

**Mac / Linux**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://localhost:8000.

- **Admin password:** if `ADMIN_PASSWORD` is empty in `.env`, the terminal prints a generated admin password on first start. You'll be asked to change it after signing in. To choose it yourself, set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env` *before* the first start.
- **Also set `APP_SECRET_KEY`** to any long random string, so saved Azure connections keep working after a restart.
- **The demo:** click **Explore the demo** on the sign-in page.

Next time you only need:
```bat
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

Upgrading from an older CloudPulse: delete `backend\cloudpulse.db` once. Cloud data is fetched again automatically.

### Account commands

```bash
python -m app.manage list                         # everyone who can sign in
python -m app.manage workspaces                   # workspace names (slugs)
python -m app.manage create-user person@company.com --workspace my-azure-subscription --role owner
python -m app.manage reset-password person@company.com
python -m app.manage create-admin second.admin@company.com
```

---

## 3. Connect your Azure subscription

Everything below runs in **Azure Cloud Shell**, so you don't need to install anything:

1. Open https://portal.azure.com.
2. Click the `>_` icon in the top bar and choose **Bash**. If it asks about storage, pick **No storage account required**.
3. Upload `cloudpulse.zip` with the **Upload** button in the Cloud Shell toolbar.
4. Unzip it and move into the folder:

```bash
unzip -q cloudpulse.zip -d cloudpulse && cd cloudpulse
```

The scripts read your subscription's allowed regions (Azure for Students limits these) and pick one. To choose it yourself, put `LOCATION=southindia` in front of the command.

| Script | What it does | Cost from your credit |
|---|---|---|
| `bash scripts/azure/01-workload.sh` | A small "company": VM, web app, SQL database, storage. Gives CloudPulse real spend across several services | about $2/day |
| `bash scripts/azure/02-leaks.sh` | Planted waste with no tags: an unattached disk, an unused static IP, an orphaned snapshot, a VM that's stopped but still billed | about $0.30/day |
| `bash scripts/azure/03-reader-identity.sh` | A read-only identity (Reader + Cost Management Reader). Prints the four values CloudPulse needs | free |
| `bash scripts/azure/04-deploy-app.sh` | Deploys CloudPulse to App Service with a managed identity (no secrets), and asks you for the admin email and password | about $13/month |
| `bash scripts/azure/05-spike.sh up` / `down` | Scales the workload up for a day, creating a real anomaly | about +$7 for that day |
| `bash scripts/azure/06-custom-domain.sh app.yourdomain.in` | Puts CloudPulse on your .in domain with free HTTPS | free |
| `bash scripts/azure/99-cleanup.sh` (`--all`) | Deletes the workload and planted waste (`--all` also removes the app and the identity) | — |

**Timing:** Azure publishes cost data 8 to 24 hours after usage. Run `01` and `02` a day before you need the numbers. Waste and owners show up within minutes. For the anomaly, the workload needs about a week of normal days first, then run `05-spike.sh up`, and `down` a day later.

### Choose how CloudPulse signs in to Azure

- **On your laptop (simplest):**
  1. Install the Azure CLI and run `az login`.
  2. In `backend/.env`, set `AZURE_SUBSCRIPTION_ID=<your id>` and `AZURE_USE_CLI=true`.
  3. Restart the app. A workspace called `WORKSPACE_NAME` appears, already connected.
- **On your laptop or any host, with a read-only identity:**
  1. Run `03-reader-identity.sh`.
  2. Either paste the four values into **Workspaces & users → Connect Azure**, or put them in `.env`.
- **On Azure App Service:** `04-deploy-app.sh` does everything. The app uses its managed identity, so no secret exists at all.

Treat the client secret like a password. Keep it out of chats, screenshots and git.

A step-by-step guide with the exact `.env` names is in [docs/REAL_AZURE_SETUP.md](docs/REAL_AZURE_SETUP.md).

---

## 4. First steps as administrator

1. Sign in with the admin account and open **Workspaces & users**.
2. If you connected Azure through `.env` or the deploy script, the workspace is already there.
   - Otherwise, click **New workspace** and then **Connect Azure**.
3. Click **Add person** on that workspace.
   - Enter the customer's email and choose **Owner** or **Viewer**.
   - CloudPulse shows a temporary password once. Send it to them privately.
4. They sign in, choose their own password, and see only their workspace.

---

## 5. Put it on your .in domain

**On Azure (recommended with your credit):**

1. Run `04-deploy-app.sh`, then `06-custom-domain.sh app.yourdomain.in`.
2. The script tells you exactly which CNAME and TXT records to add at your registrar, waits for them, and then attaches a free certificate.
3. For the bare domain (`yourdomain.in`), set up forwarding at your registrar to `https://app.yourdomain.in`.

**On Render (free tier, no Azure hosting):**

1. Push this folder to GitHub (without `backend/.env`), then choose **New → Blueprint** in Render.
2. In the service's Environment tab, set `ADMIN_EMAIL`, `ADMIN_PASSWORD` and the Azure service-principal values.
3. Add your domain under **Settings → Custom Domains**.
4. Keep in mind that the free plan sleeps when idle and has no persistent disk.

---

## 6. What's on each page

| Page | What it shows |
|---|---|
| **Overview** | Summary sentence, key figures, the finding→verified-saving funnel, daily spend with anomalies ringed, "fix these first", the month forecast, top services and owners |
| **Findings** | The inbox: tabs (to do / fixed, checking / verified / dismissed & snoozed / all), filters by kind, priority and assignee, search, CSV. Click a row for the full finding |
| **Finding drawer** | Impact and its basis, verification (before/after chart), the evidence with the actual numbers and rule, why it scored what it did, the owner trail, copy-ready fix commands, billed cost of the resource, and the complete history |
| **Anomalies** | Every flagged day: amount vs usual, z-score, what drove it, the resources behind it, and whether spend has come back down |
| **Budgets** | Budget, spend so far, forecast with its 80% range and the date the budget is passed, plus the model's own parameters |
| **Owners** | One row per person: open, verified savings, median days to fix, and their open findings |
| **Savings** | The ledger: verified savings per month, estimate vs actual with accuracy, per person, and what's still being checked |
| **Cost explorer** | Spend by service or provider, sortable table with change vs. the previous period, CSV download |
| **Data sources** | Connection status and errors, imported bills, FOCUS upload |
| **Workspaces & users** *(admin)* | Workspaces, cloud connections, people, password resets |
| **Audit log** *(admin)* | Every sign-in, change and action, searchable, with CSV |

---

## 7. How it's put together

```
backend/app/
  main.py            app start-up, background sync, sign-in redirects, security headers
  config.py          settings from the environment / .env
  models.py          users, workspaces, memberships, sessions, connections, cloud data
  security.py        password hashing, sessions, rate limiting, secret encryption
  bootstrap.py       first admin, demo workspace, workspace from server settings
  deps.py            who's signed in, which workspace they may see, owner-only checks
  manage.py          command-line account tools
  jobs.py            background sync queue (APScheduler), run status and progress steps
  audit.py           the audit trail
  routers/auth.py    sign in, demo, sign out, change password
  routers/admin.py   workspaces, Azure connections, people, audit log
  routers/api.py     overview, findings, finding detail, actions, savings, owners,
                     anomalies, month/forecast, explorer, notifications, sync, import
  services/
    analytics.py             anomaly detection, forecasting, priority, VM verdicts, before/after
    azure_rest.py            small ARM REST client: retries, paging, Resource Graph
    prices.py                Azure Retail Prices with a 7-day cache and built-in fallbacks
    azure_collector.py       costs per resource, inventory, metrics, Advisor, activity log
    aws_collector.py         Cost Explorer; EBS, EIP, EC2; CloudTrail owners
    workspace_detectors.py   anomalies, budget risk, untagged spend
    owners.py                audit-log owner lookup, cached, tags as fallback
    findings.py              fingerprints, lifecycle, permissions, verification, the ledger
    collection_orchestrator.py  one sync per workspace, signals -> findings -> verification
    demo_data.py             the scripted demo month
    focus_importer.py        any FOCUS billing export
  tests/             24 tests: hand-computed algorithm checks + a full loop against a fake Azure
backend/static/      sign-in page and app (plain HTML/CSS/JS, SVG charts, self-hosted fonts)
backend/data/        FinOps Foundation FOCUS 1.0 sample bill (CC BY 4.0), used by the demo
scripts/azure/       the Cloud Shell scripts above
```

## 8. The algorithms, in plain terms

Every number in the app comes from one of these. They're all in `backend/app/services/analytics.py` and covered by tests.

**Anomaly detection (robust z-score).** Baseline = the same weekday in the previous 4 weeks (at least 3 of them), otherwise the previous 14 days. Usual = median; swing = 1.4826 × median absolute deviation, floored at 5% of the median. A day is flagged when z > 3.5 *and* it is at least $1 and 20% above usual. The increase is split by service, then by resource. If the next two days stay above halfway up the spike, it's "still running high" and the impact becomes excess × 30.4.

**Forecast (Holt's linear smoothing).** α and β are grid-searched over 12 combinations, keeping the smallest one-day-ahead error. With 28+ days each weekday gets a factor (clipped 0.5–1.5). The 80% range is ±1.2816 × RMSE × √(days left), and the budget breach date is the first day the cumulative forecast passes the budget. Fewer than 7 billed days falls back to a simple average.

**Priority score.** `100 × (0.6 × impact_score + 0.4 × severity_weight) × confidence × age_factor`, where `impact_score = log₁₀(1 + monthly $) ÷ log₁₀(1001)`, severity is critical/high/medium/low = 1.0/0.8/0.55/0.3 (set by dollar size), and `age_factor = 1 + min(0.3, days_open ÷ 100)`. Bands: P1 ≥ 70, P2 ≥ 45, P3 ≥ 25, P4 below. Governance findings count a quarter of their dollars, since the money isn't wasted, only unattributed. A fixed finding stops ageing on the day it was fixed.

**VM verdicts.** From 14 days of hourly metrics (at least 48 points): *idle* when p95 CPU < 5% and p95 network < 5 MB/h; *oversized* when p95 CPU < 20% and peak < 80%, with the next size down taken from a size ladder. Confidence 0.85 with a full week of metrics, 0.65 otherwise, minus 0.15 for a resize. Azure Advisor agreeing adds 0.05.

**Verification (before/after).** Average daily billed cost for the resource over the 7 days before the fix vs the days after (at least 3, up to the last billed day). Realised monthly saving = (before − after) × 30.4, never negative. If nothing dropped, CloudPulse keeps waiting for up to 14 days rather than claiming a saving. Accuracy = realised ÷ estimated, which is how the ledger can tell you how good its own estimates are.

**Finding lifecycle.** Each signal gets a SHA-256 fingerprint so it stays the same finding across syncs. A finding that stops being detected is resolved automatically; one marked fixed but still detected 30 minutes later reopens; a verified finding whose problem returns reopens and its saving is withdrawn.

---

## 9. Running the tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q tests
```

`tests/test_analytics.py` checks the maths against numbers worked out by hand. `tests/test_engine.py` runs a whole subscription through the loop against a fake Azure: detection and pricing, owner lookup and auto-assignment, permissions, reopening, verification with real before/after numbers, a regression that withdraws a saving, and the audit trail.

---

## 10. Limits to mention if asked

- Where CloudPulse has the resource's own billed cost it uses that; otherwise figures are list-price estimates, before discounts or credits. Each finding says which basis it used.
- Owner history covers the audit log's 90-day window. Older resources fall back to tags, or to a manual assignment.
- Notifications are in-app only (the bell). No email is sent.
- Verification needs per-resource cost data, so it works for Azure resources CloudPulse can match to the bill; anomalies are verified by the spend coming back down instead.
- Azure connections can be added in the app. AWS connections come from server settings for now.
- SQLite is fine for a single server. For more than one instance, set `DATABASE_URL` to PostgreSQL (and add `psycopg2-binary` to requirements.txt).
- Google Cloud and Oracle Cloud are read through FOCUS imports only.
