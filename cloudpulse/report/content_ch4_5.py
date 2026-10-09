"""Chapters 4-5: Architecture Diagram, Methodology."""
D = "diagrams/"


def chapter4(r):
    r.h(1, "4. ARCHITECTURE DIAGRAM")
    r.h(2, "4.1  Overview of the Architecture")
    r.para("CloudPulse is a three-tier web application that talks to a customer's Azure subscription. The **client tier** is a "
           "browser running a single-page application. The **server tier** is one Python process that contains the API, the "
           "security layer, the scheduler and all business logic. The **data tier** is a SQL database together with the "
           "server's configuration. The cloud itself is an external system: CloudPulse only ever reads from it, after "
           "proving its identity to Microsoft Entra ID. Section 4.2 describes the layers; Figure 4.1, on the full page that follows it, shows all components and the numbered "
           "flows between them, with the Azure credential path highlighted. The numbers are explained in Table 4.1.")
    r.h(2, "4.2  Layers of the System")
    r.h(3, "4.2.1  Client tier")
    r.para("The browser application has no build step. It calls the JSON API, keeps its state in memory, and renders ten pages: "
           "Overview, Cost explorer, Anomalies, Budgets, Findings, Owners, Savings, Data sources and, for administrators, "
           "Workspaces & users and the Audit log. A header on every state-changing request (`X-CloudPulse: 1`) lets the server "
           "reject forged cross-site form posts. Four kinds of people use it: the administrator who sees every workspace, a "
           "customer owner who can sync and set budgets, a customer viewer who can only look, and an anonymous demo visitor "
           "who sees sample data in read-only mode.")
    r.h(3, "4.2.2  API and security layer")
    r.para("Three FastAPI routers expose the system: `/api/auth` (login, demo, logout, current user, password change), "
           "`/api/admin` (workspaces, Azure connections, users, memberships, audit) and `/api/*` (overview, explorer, month "
           "forecast, findings and their actions, savings, owners, notifications, budget, FOCUS upload, connections). Every "
           "request is authenticated by a server-side session, authorised against the user's role in the requested "
           "workspace, and logged where it changes data. Failed logins are limited to 8 attempts per 15 minutes per e-mail "
           "and per client address.")
    r.h(3, "4.2.3  Service layer")
    r.para("The **collection orchestrator** coordinates one synchronisation. The **Azure collector** wraps the custom ARM client "
           "and converts API answers into *signals*. **Detectors and analytics** are pure functions without database or "
           "network access, which makes them easy to test. The **findings engine** turns signals into findings with a "
           "fingerprint, a priority and a lifecycle, and runs the verification pass. The **owner resolver** finds the "
           "creator of each resource and caches the answer; the **price book** looks up Azure retail prices and caches "
           "them for seven days with built-in fallback tables for when the public API cannot be reached.")
    r.h(3, "4.2.4  Data tier")
    r.para("All state is in one relational schema (Table 4.3). SQLite is the default because it needs no installation; "
           "setting `DATABASE_URL` to a PostgreSQL address moves the same schema to a production database.")
    r.h(2, "4.3  Azure Credential Architecture")
    r.para("Everything CloudPulse knows about an Azure subscription comes through one identity. This section explains the "
           "Azure concepts involved and how the application keeps that identity safe.")
    r.h(3, "4.3.1  Concepts")
    r.bullets([
        "**Tenant.** A Microsoft Entra ID directory that represents an organisation. Its identifier (tenant ID) is part of the "
        "token URL [11].",
        "**Subscription.** The billing and resource container that CloudPulse monitors. Its subscription ID appears in every "
        "ARM request path.",
        "**App registration and service principal.** An app registration defines an application identity (the **client ID**, "
        "also called the application ID). The service principal is its instance inside the tenant, the object to which roles "
        "are assigned.",
        "**Client secret.** A password generated for the app registration. CloudPulse needs it only to prove that the "
        "request really comes from the registered application. Secrets expire; the script issues one valid for one year.",
        "**Role-based access control (RBAC).** Permissions are granted as role assignments at a scope. CloudPulse is given "
        "**Reader** (list resources, read metrics and the Activity Log) and **Cost Management Reader** (read costs) on "
        "`/subscriptions/{id}` only [18]. Neither role can create, change or delete anything.",
        "**Access token.** The result of a successful sign-in: a signed JSON Web Token valid for about an hour. Every ARM "
        "request carries it in the `Authorization: Bearer` header; ARM checks the signature and the role assignments before answering.",
    ])
    # landscape page with the figure
    r.landscape_section()
    r.figure(D + "fig_architecture.png", "Figure 4.1: CloudPulse system architecture with the Azure credential and data flows",
             width_cm=24.6)
    r.portrait_section()
    r.para("Table 4.1 explains every numbered flow of Figure 4.1; the credential-related steps (0, 2, 4, 5, 6, 7 and 8) are detailed in Section 4.3.2.")
    r.table("Table 4.1: Numbered flows in Figure 4.1",
            ["Step", "Flow", "What happens"],
            [["0", "Operator → Entra ID, RBAC", "One-time setup in Azure Cloud Shell: an app registration and service principal are created and the roles Reader and "
              "Cost Management Reader are granted at subscription scope"],
             ["1", "Browser → API", "A user signs in over HTTPS; the server checks the scrypt hash and sets an HttpOnly session cookie"],
             ["2", "API → credential store", "The administrator submits subscription, tenant, client ID and client secret; the secret is encrypted with Fernet before it is stored"],
             ["3", "Scheduler → orchestrator", "Every 6 hours, or when Sync is pressed, a collection run starts for each workspace"],
             ["4", "Credential store → collector", "The connection is read and the secret decrypted in memory (or the server settings are used)"],
             ["5", "Collector → Entra ID", "OAuth 2.0 client-credentials request for the scope management.azure.com/.default"],
             ["6", "Entra ID → collector", "A short-lived JWT access token (about one hour) is returned and cached"],
             ["7", "Collector → ARM", "Read-only REST calls with the Bearer token: cost, inventory, metrics, Activity Log, Advisor"],
             ["8", "ARM → collector", "ARM validates the token and the role assignment, then returns JSON, or 403 / 404 / 429"],
             ["9", "ORM → database", "Costs, findings, owners and events are written in a transaction"],
             ["10", "Database → ORM → API", "The interface reads findings, charts and forecasts through the same API"]],
            widths=[1.2, 4.2, 9.6], size=10)
    r.para("The credential concepts above lead to three practical ways of signing in, compared in Table 4.2.")
    r.table("Table 4.2: Three ways CloudPulse can sign in to Azure",
            ["Method", "Settings", "Where the secret lives", "Typical use"],
            [["Service principal", "AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET (or the Connect Azure form)",
              "Server settings, or encrypted in the connections table", "CloudPulse on a laptop or any host outside Azure"],
             ["Azure CLI login", "AZURE_USE_CLI=true after `az login`", "Azure CLI token cache on the same machine", "Quick local demonstration"],
             ["Managed identity", "AZURE_USE_MANAGED_IDENTITY=true", "None: Azure issues the token to the App Service", "CloudPulse deployed on Azure App Service"]],
            widths=[2.8, 5.6, 3.8, 2.8], size=9.5)
    r.h(3, "4.3.2  Sign-in and request sequence")
    r.para("Figure 4.2 shows the complete sequence, from the one-time creation of the identity to a single read call. In "
           "phase B the `ClientSecretCredential` class posts the client credentials to the tenant's token endpoint and "
           "caches the returned token. In phase C each collector call attaches the token; if the answer is HTTP 403 the "
           "message \"Signed in, but this identity has no Reader role on the subscription\" is shown to the "
           "administrator, and if it is HTTP 429 the client waits for the `Retry-After` period and tries again, up to a "
           "fixed number of attempts.")
    r.figure(D + "fig_credflow.png", "Figure 4.2: Azure credential creation, token acquisition and read-only request sequence",
             width_cm=11.6)
    r.h(3, "4.3.3  Protecting the credentials")
    r.bullets([
        "**Least privilege.** The identity is read-only and limited to one subscription; leaking it would expose information "
        "but not allow any change.",
        "**Encryption at rest.** A client secret entered in the interface is encrypted with **Fernet** (AES-128-CBC with an "
        "HMAC-SHA256 integrity check) using a key derived by SHA-256 from the server's `APP_SECRET_KEY`. Only the token is "
        "stored; the API never returns it, and the interface shows only whether it can still be read.",
        "**No secret at all on Azure.** When deployed on App Service the managed identity [19] needs no stored credential.",
        "**Separation of settings.** Credentials in `.env` are excluded from version control by `.gitignore`; the README warns "
        "never to place secrets in chats, screenshots or git.",
        "**Rotation.** Because the secret expires after a year, the setup script can be run again to issue a new one, and the "
        "old connection can be replaced in the administrator page.",
        "**Early diagnosis.** The command `python -m app.manage check-azure` signs in with the configured settings and "
        "reports either \"Connected\" with the subscription name or the exact reason for failure.",
    ])
    r.h(2, "4.4  Data Model")
    r.table("Table 4.3: Database tables",
            ["Table", "Purpose", "Key columns"],
            [["users, memberships", "Accounts and their role (owner / viewer) in each workspace", "email, password_hash (scrypt), is_admin, must_change_password"],
             ["sessions", "Server-side login sessions, 12-hour lifetime", "token hash, expiry"],
             ["workspaces", "One organisation's cloud data; kind is customer or demo", "slug, name, kind"],
             ["connections", "Cloud accounts of a workspace", "provider, auth (env / service_principal / cli / managed_identity), config JSON, secret (Fernet)"],
             ["cost_snapshots", "Daily cost by service and provider", "day, service, provider, amount"],
             ["resource_costs", "Daily cost of single resources (used for verification)", "resource_id, day, amount"],
             ["resource_owners", "Cached creator of each resource", "principal, source, checked_at"],
             ["findings", "One row per problem, unique by fingerprint", "kind, monthly_impact, priority_score, status, assignee_id, realized_monthly, evidence JSON"],
             ["finding_events", "History of a finding", "kind, message, actor, at"],
             ["notifications", "In-app inbox", "user_id, message, read"],
             ["audit_log", "Sign-ins and administrative changes", "actor, action, detail, at"],
             ["price_cache, settings, collection_runs", "Retail price cache, workspace budget, sync history", "sku, price, step, status"]],
            widths=[3.6, 6.0, 5.4], size=9.5)
    r.h(2, "4.5  Deployment Architecture")
    r.para("The same container image runs in four settings. On a laptop the application starts with `uvicorn` and a SQLite "
           "file. With Docker Compose a named volume keeps the database between restarts. On Render the blueprint `render.yaml` "
           "builds the Dockerfile, generates a random `APP_SECRET_KEY`, and exposes a health check at `/api/health`. On "
           "Azure App Service the script `04-deploy-app.sh` creates the web app, enables its managed identity, grants it "
           "the two reader roles and asks for the administrator's e-mail and password, so that no cloud secret is stored "
           "anywhere. A custom domain with a free HTTPS certificate can be attached with `06-custom-domain.sh`.")
    r.h(2, "4.6  Security Architecture")
    r.table("Table 4.4: Threats and the controls that address them",
            ["Threat", "Control in CloudPulse"],
            [["Stolen password database", "scrypt (N = 2^14, r = 8, p = 1) with a random salt per user; temporary passwords must be changed at first sign-in"],
             ["Password guessing", "Rate limit of 8 failures per 15 minutes; generic error text"],
             ["Session theft", "Random token, only its SHA-256 hash is stored; HttpOnly, SameSite=Lax and (on HTTPS) Secure cookie; 12-hour lifetime"],
             ["Cross-site request forgery", "Every non-GET request must carry the custom `X-CloudPulse` header, which a foreign site cannot set"],
             ["Leaked cloud credential", "Read-only roles on one subscription; Fernet encryption at rest; managed identity option with no secret"],
             ["Cross-tenant access", "Every query is scoped by workspace and checked against the user's membership"],
             ["Clickjacking and sniffing", "X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy same-origin"],
             ["Abuse of the demo", "Demo user is read-only and bound to the sample workspace only"],
             ["Accidental change to the cloud", "The collector issues only GET requests and the Cost Management and Resource Graph query POSTs"]],
            widths=[4.2, 10.8], size=10)


def chapter5(r):
    r.h(1, "5. METHODOLOGY")
    r.h(2, "5.1  Development Approach")
    r.para("The project followed an incremental, test-first approach. The algorithms were written first as pure Python functions "
           "with unit tests whose expected values were calculated by hand, then the Azure collector was added and tested "
           "against a fake cloud, then the findings engine and API, and finally the user interface. A scripted Azure "
           "workload was created so that the same code could be proven on a real subscription. Each stage kept the "
           "previous tests passing; the final suite contains 27 tests.")
    r.h(2, "5.2  The Cost-to-Action Loop")
    r.para("The loop of Chapter 1 maps one-to-one to software modules: signals come from `azure_collector.py` and "
           "`workspace_detectors.py`; context from `prices.py` and the cost tables; findings and priority from `findings.py` "
           "and `analytics.py`; ownership from `owners.py`; action from the routers and `findings.act`; verification "
           "from `findings.verify`. The central data structure is the **signal**, a plain dictionary with a kind, a "
           "resource, a monthly impact, a confidence, evidence and suggested fix commands. A signal that survives "
           "de-duplication becomes a **finding**.")
    r.h(2, "5.3  Data Collection")
    r.para("A synchronisation is one function call, `sync_workspace`, executed by APScheduler or by the Sync button (Figure 5.1). "
           "It is deliberately fault tolerant: every collection step records its own error, so a permission problem with "
           "Azure Advisor does not stop the cost data from loading, and the Data sources page shows which step failed and why.")
    r.figure(D + "fig_pipeline.png", "Figure 5.1: The synchronisation pipeline executed on every sync", width_cm=12.6)
    r.para("**Cost data.** The Cost Management query API is called with an `ActualCost` definition, daily granularity and "
           "grouping by service, and again by resource. The first sync back-fills 90 days; later syncs re-read only the "
           "last 10 days because Azure revises recent days. **Inventory.** A single Resource Graph query lists every "
           "resource, and a second returns disks, public IPs, snapshots and VMs with the properties needed for detection. "
           "Resource Graph answers are paged with `$skipToken`. **Usage.** For each running VM, hourly CPU and network "
           "metrics for the previous 14 days are requested from Azure Monitor. **Advice.** Azure Advisor cost "
           "recommendations are read and merged into matching findings as supporting evidence.")
    r.h(2, "5.4  Detection Rules")
    r.table("Table 5.1: Waste detection rules applied to the Azure inventory",
            ["Finding", "Rule", "Monthly impact", "Confidence"],
            [["Unattached disk", "`diskState = Unattached`", "Size × list price of the disk tier (retail price API, fallback table)", "0.95"],
             ["Idle public IP", "Static allocation, no `ipConfiguration`, no NAT gateway", "Standard public IP list price", "0.95"],
             ["Orphaned snapshot", "Source disk no longer exists; or older than 30 days", "Size × snapshot price", "0.90 / 0.60"],
             ["VM stopped but billed", "Power state `stopped` (not deallocated)", "Hours per month × VM list price + attached disks", "0.90"],
             ["Deallocated VM", "Power state `deallocated`; disks still billed", "Attached disks only", "0.60"],
             ["Idle VM", "p95 CPU < 5 % and p95 network < 5 MB per hour over the window", "Compute price of the size", "0.85 (0.65 if < 7 days)"],
             ["Oversized VM", "p95 CPU < 20 % and peak CPU < 80 %; smaller size on the ladder exists", "Price difference to the next smaller size", "0.70 (0.50)"],
             ["Advisor item", "Azure Advisor, category Cost", "Annual saving ÷ 12 as published by Advisor", "0.80 / 0.70 / 0.60 by Advisor impact"]],
            widths=[2.8, 5.0, 4.4, 2.8], size=9.5)
    r.para("Where Cost Management already reports the billed cost of a resource over the last days, the **actual cost** replaces "
           "the list-price estimate, because enterprise agreements and reservations make list prices unreliable. The "
           "finding records which basis was used (\"list price\" or \"billed cost\"). For VMs, memory cannot be measured "
           "without a guest agent, so the oversized verdict is always 0.15 less confident than the idle verdict.")
    r.h(2, "5.5  Ownership Attribution")
    r.para("For every resource that produced a signal, CloudPulse queries the Activity Log (management events of the last "
           "89 days) filtered to that resource. It selects the **earliest successful `/write` operation**, whose `caller` "
           "field is either a user principal name, or a GUID for an application or managed identity. A GUID caller is "
           "described as a \"service identity\" together with its application ID. If the Activity Log has no event, the "
           "tags `owner`, `createdby`, `created-by`, `created_by`, `contact` and `team` are tried in that order. The result "
           "is cached in `resource_owners`; known owners are kept, unknown ones are retried once a day. A person matched by "
           "e-mail to a CloudPulse user receives the finding as an assignment and a notification.")
    r.h(2, "5.6  Anomaly Detection")
    r.para("A good anomaly detector must ignore normal weekly rhythm, such as lower spend at weekends, and must not be "
           "fooled by earlier anomalies. CloudPulse therefore uses a **robust, weekday-aware z-score** based on the "
           "median and the median absolute deviation (MAD), with the cut-off of 3.5 recommended for modified z-scores [8]. "
           "For each billed day *x*:")
    r.code("""B = same weekday, previous 4 weeks (>= 3 of them), else previous 14 days
m = median(B)
s = max(1.4826 x MAD(B), 0.05 x m, 0.01)     # floor: a flat history cannot give s = 0
z = (x - m) / s
flag the day when  z > 3.5  and  (x - m) >= max(1.00, 0.20 x m)""")
    r.para("At least seven billed days are required. The **drivers** of a flagged day are found by comparing each service with "
           "its own median on the baseline days; the increases are expressed as shares that add up to 100 %. A spike is "
           "**ongoing** if the next two days both stay above *m* plus half the excess; the impact is then projected as "
           "excess × 30.4 days, otherwise it is the one-off excess. Confidence grows with the z-score: "
           "min(0.95, 0.55 + 0.05 × (z − 3.5)). **Worked example (demo data, Tuesday 24 September 2024):** the baseline "
           "was the three earlier Tuesdays (3, 10 and 17 September) with a median of $73.55 and a robust spread of $12.11. The "
           "day cost $169.26, an excess of $95.71 (2.3 times the usual), giving z = 95.71 / 12.11 = 7.9, far above 3.5. "
           "Amazon Elastic Compute Cloud explains 99.1 % of the increase (from a usual $19.04 to $164.14). Both "
           "following days stayed high, so the spike is *ongoing* and its monthly impact is 95.71 × 30.4 = $2,909.55, with confidence "
           "0.55 + 0.05 × (7.9 − 3.5) = 0.77. The day is shown in Figure 6.4.")
    r.h(2, "5.7  Forecast and Budget Breach")
    r.para("Month-end spend is forecast with **Holt's linear exponential smoothing** [9], [10], a method that tracks a level and "
           "a trend. Before fitting, each day is divided by a **weekday factor** (the weekday's average over the overall "
           "average, clipped to the range 0.5 to 1.5), which needs four weeks of data. Smoothing constants are chosen "
           "by trying every pair from α ∈ {0.2, 0.4, 0.6, 0.8} and β ∈ {0.05, 0.1, 0.2} and keeping the pair with the smallest "
           "one-step-ahead squared error. Each remaining day *h* is projected as")
    r.code("""forecast(h) = max(0, level + h x trend) x weekday_factor(day)
month_end   = month_to_date + sum(forecast(h))
80% range   = month_end +/- 1.2816 x RMSE x sqrt(days_left) x mean(factors)
breach date = first day on which the running total passes the budget""")
    r.para("With fewer than seven billed days the average of the days so far is used, and once the month is complete the "
           "forecast equals the actual total. A **budget risk** finding is raised when the forecast passes the budget. "
           "In the demo data the $2,600 budget was passed on 28 September, ending the month at $2,829.99, 9 % over.")
    r.h(2, "5.8  Priority Score")
    r.para("Findings differ in money, urgency and certainty, so CloudPulse combines them into one number from 0 to 100:")
    r.code("""score = 100 x (0.6 x impact_score + 0.4 x severity_weight)
              x confidence x age_factor
impact_score    = min(1, log10(1 + impact) / log10(1 + 1000))
                  # $10 -> 0.35, $100 -> 0.67, $1,000 -> 1.0
severity_weight = critical 1.0 | high 0.8 | medium 0.55 | low 0.3
                  # severity from impact: >= 500, >= 100, >= 20, else low
age_factor      = 1 + min(0.3, days_open / 100)     # up to +30 %
band            = P1 >= 70 | P2 >= 45 | P3 >= 25 | P4 otherwise""")
    r.para("The logarithm prevents one very large item from hiding all others, and the age factor gradually raises forgotten "
           "findings. Governance findings such as untagged spend count only 25 % of their dollar value, because that spend "
           "is not wasted. **Worked example:** a stopped VM costing $70.08 a month with confidence 0.9 has impact_score "
           "log10(71.08)/log10(1001) = 0.617 and medium severity (0.55), so the score is 100 × (0.6 × 0.617 + 0.4 × 0.55) × "
           "0.9 = 53 (P2). After 30 days open the age factor is 1.3 and the score becomes 69, still P2. Figure 5.3 plots the "
           "function for the four severities.")
    r.figure(D + "fig_priority.png", "Figure 5.3: Priority score against monthly impact (confidence 0.9, new finding), produced by the implemented function",
             width_cm=12.0)
    r.h(2, "5.9  Finding Lifecycle")
    r.para("A finding moves through the states of Figure 5.2. Permissions are role based: administrators and workspace owners "
           "may perform every action, the assignee may start and resolve their own finding, viewers and the demo user may "
           "only read. Dismissing requires a written reason of at least three characters and snoozing is limited to 1 to 90 "
           "days. Each action writes a `finding_event`, updates the score, and notifies the assignee. A finding is "
           "identified by a **fingerprint**, a SHA-256 hash of its kind and resource, so that the same problem found on "
           "consecutive syncs updates one row instead of creating many.")
    r.figure(D + "fig_lifecycle.png", "Figure 5.2: Finding lifecycle, with automatic and manual transitions", width_cm=13.0)
    r.h(2, "5.10  Saving Verification")
    r.para("Verification is what distinguishes CloudPulse from a report generator. When a finding is marked resolved, the next "
           "sync checks that the resource is no longer detected (a 30-minute grace period tolerates delay in Azure). Then "
           "the billed cost is compared:")
    r.code("""before = mean daily cost of the resource, 7 days before the fix day
after  = mean daily cost, up to 7 days after the fix (billed days only)
realised_monthly = max(0, before - after) x 30.4
verify only when at least 3 'after' days exist""")
    r.para("If the cost has not dropped yet the finding waits, up to 14 days; a resource with no billed history is verified "
           "with its estimate and the method is recorded. A verified saving shows the **estimate accuracy**, the realised "
           "saving divided by the estimate. Anomalies are verified when the last three billed days are back within half "
           "the spike. If a verified resource appears again, the finding is reopened and the saving is withdrawn.")
    r.h(2, "5.11  Notifications, Audit and Export")
    r.para("Assignments, comments, resolutions, dismissals and verifications create notifications that appear under the bell "
           "icon with an unread counter. Sign-ins, failed sign-ins, user changes, connection changes and syncs are written to "
           "the audit log. The findings list can be searched, filtered by kind, priority and assignee, and exported to CSV.")
    r.h(2, "5.12  The Azure Test Environment")
    r.para("To demonstrate CloudPulse on a real subscription, a set of Bash scripts creates a small company and then plants "
           "waste. They read the subscription's allowed regions, register the needed resource providers, and ask for "
           "confirmation before changing anything.")
    r.table("Table 5.2: Azure scripts",
            ["Script", "Action", "Approx. cost"],
            [["01-workload.sh", "VM, App Service plan and web app, Azure SQL Basic database, storage account with sample data", "$2 / day"],
             ["02-leaks.sh", "Plants four untagged wasted resources (Table 5.3)", "$0.30 / day"],
             ["03-reader-identity.sh", "Creates the read-only service principal and prints the four values CloudPulse needs", "free"],
             ["04-deploy-app.sh", "Deploys CloudPulse to App Service with a managed identity", "about $13 / month"],
             ["05-spike.sh up | down", "Scales the workload for a day to create a real anomaly", "about $7"],
             ["06-custom-domain.sh", "Attaches a custom domain with free HTTPS", "free"],
             ["99-cleanup.sh [--all]", "Deletes the test resources (and the app and identity with --all)", "-"]],
            widths=[4.0, 8.4, 2.6], size=10)
    r.table("Table 5.3: Waste planted by 02-leaks.sh and the finding CloudPulse raises",
            ["Planted resource", "Azure command used", "Finding raised"],
            [["leftover-disk (4 GB)", "az disk create (not attached)", "Unattached disk"],
             ["unused-ip", "az network public-ip create (Standard, static)", "Idle public IP"],
             ["old-backup-snap", "snapshot of temp-disk, then the disk is deleted", "Orphaned snapshot"],
             ["forgotten-vm", "az vm create then az vm stop (not deallocate)", "VM stopped but still billed"]],
            widths=[4.2, 6.6, 4.2], size=10)
    r.para("None of the planted resources has an owner tag; CloudPulse must find the creator from the Activity Log, which is "
           "exactly the capability being demonstrated. Because Azure publishes costs 8 to 24 hours late, the scripts are run "
           "a day before a demonstration; waste and owners appear within minutes, while cost charts follow later.")
    r.h(2, "5.13  Testing Strategy")
    r.table("Table 5.4: Automated tests (27)",
            ["File", "Tests", "What is verified"],
            [["tests/test_analytics.py", "23", "median, percentile and MAD; flat series raises no anomaly; spike detection with weekday baseline and drivers; ongoing spike "
              "projection; small increases ignored; 7-day minimum; 14-day fallback; forecast for complete, constant, linear and short series; priority "
              "values and bands; governance down-weighting; severity tiers; VM idle / oversized / fine; size ladder; before/after for deleted, "
              "waiting and partial drops; saved-to-date"],
             ["tests/test_engine.py", "1", "Full loop with a fake Azure cloud: sync, findings, owners, assign, start, dismiss, resolve, reopen, verify, "
              "ledger, permissions (a viewer may resolve their own finding but not dismiss), regression when a fixed resource returns, audit trail"],
             ["tests/test_static.py", "3", "CSS colour tokens are valid and opaque; every page has a renderer; Azure setup diagnostics explain what is missing"]],
            widths=[3.6, 1.4, 10.0], size=9.5)
    r.para("Beyond unit tests, every page was loaded in headless Chromium at desktop width and at 400 pixels, with the "
           "browser console checked for errors. This check found a real defect: a mistyped colour value in the style sheet "
           "made the main text almost transparent. It was corrected and a regression test was added.")
