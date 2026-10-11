"""Text content of the PD Lab III report (CloudPulse), organised in the sample's chapter structure."""

TITLE = "CLOUDPULSE: CLOUD COST MONITORING AND OPTIMISATION PLATFORM"
TITLE_SHORT = "CLOUDPULSE"
TEAM = [("TAMIL MANI B", "111624102217"), ("THEJA J G", "111624102225"),
        ("VARUNESH D", "111624102235"), ("VISWAJITH R", "111624102242")]

ABSTRACT = [
    "Organisations and students who run workloads on Microsoft Azure and Amazon Web Services often pay for resources that nobody "
    "uses. A virtual machine shut down from inside the operating system still bills for compute, a detached disk keeps charging for "
    "every gigabyte, and an unused public IP address and an orphaned snapshot add cost every day. Native cost consoles show how "
    "much was spent but do not say who owns the waste, what to fix first, or whether a fix really saved money.",
    "To address this, we developed CloudPulse, a cloud cost monitoring and optimisation platform. It connects to an Azure "
    "subscription with a read-only service principal that holds only the Reader and Cost Management Reader roles, and reads the bill, "
    "the resource inventory, virtual machine metrics, Azure Advisor recommendations and the Activity Log. Rule-based detectors and "
    "transparent statistics, a weekday-aware robust z-score for spend anomalies, Holt's linear smoothing for budget forecasts and a "
    "percentile verdict for idle and oversized virtual machines, turn this data into de-duplicated findings. Each finding is priced "
    "per month, scored from P1 to P4, assigned to the person who created the resource and tracked through a defined lifecycle.",
    "In summary, CloudPulse carries every cost problem from detection to a verified result: a saving is counted only after seven "
    "days of billed cost confirm the drop, and a fixed resource that reappears reopens its finding. The system is built with Python, "
    "FastAPI, SQLAlchemy and a framework-free JavaScript interface, protects stored cloud secrets with Fernet encryption, and is "
    "validated by 27 automated tests and a scripted Azure environment that plants real waste. In its demonstration workspace it "
    "reported $262.94 a month of open waste and $33.44 a month of verified savings at 94% estimate accuracy.",
]


def chapters():
    """Returns a list of blocks. Block kinds:
    ('ch', number, title) ('h1', 'n.n', TITLE) ('h2', 'n.n.n', TITLE) ('h3', 'n.n', TITLE)
    ('p', text) ('bul', [items]) ('num', [items]) ('obj', label, text) ('tbl', title, header, rows, widths_cm)
    ('fig', path, title, width_cm) ('figrot', path, title)  ('pb',)"""
    B = []
    a = B.append

    # ------------------------------------------------------------ CHAPTER 1
    a(("ch", 1, "INTRODUCTION"))
    a(("p", "Effective cloud cost management has become an increasingly urgent concern as organisations, start-ups and students move "
            "their workloads to public clouds. Cloud platforms such as Microsoft Azure and Amazon Web Services bill by the second or "
            "the hour, so every virtual machine, disk and network address that is created and then forgotten keeps costing money. "
            "CloudPulse is a cloud cost monitoring and optimisation platform that finds this wasted spend, assigns each problem to "
            "the person who created the resource, tracks the fix and proves the saving on the next bill. This introduction presents "
            "the background, purpose and specific benefits of the platform and shows why it matters in the wider context of "
            "responsible cloud use."))
    a(("h1", "1.1", "BACKGROUND"))
    a(("p", "Cloud computing changed how technology is bought: instead of purchasing servers in advance, a team can create a "
            "virtual machine, a database or a storage account in minutes and pay only for what it uses [1], [2]. This elasticity is "
            "the main strength of the cloud and also its main financial risk, because resources are easy to create and easy to forget. "
            "A virtual machine that was shut down from inside its operating system is reported as stopped, yet the platform still "
            "reserves its hardware and keeps billing for compute. A data disk that was detached when a project ended continues to be "
            "charged for every gigabyte it holds, and static public IP addresses and snapshots add a little more every day."))
    a(("p", "The discipline that deals with this problem is called FinOps, or cloud financial operations. The FinOps Foundation "
            "describes it as a practice in which engineering, finance and business teams share responsibility for cloud spend and "
            "make timely, data-driven decisions [3]. A central idea of FinOps is that visibility alone is not enough: a cost problem "
            "is solved only when somebody who owns it acts and the saving can be shown on the next bill."))
    a(("h1", "1.2", "PURPOSE OF CLOUDPULSE"))
    a(("p", "CloudPulse plays a crucial role in addressing diverse cloud cost issues, with specific purposes in finding wasted "
            "spend and in helping teams act on it with accountability."))
    a(("h2", "1.2.1", "FINDING WASTED CLOUD SPEND"))
    a(("p", "Native consoles such as Azure Cost Management are very good at answering how much was spent and on what. They are weaker "
            "at answering which individual resources are idle, who created each of them, what should be fixed first, whether it was "
            "really fixed and whether the waste came back. CloudPulse reads the bill, the resource inventory, virtual machine "
            "metrics, Azure Advisor recommendations and the Activity Log on every synchronisation and turns them into one ranked "
            "list of findings."))
    a(("h2", "1.2.2", "BENEFITS FOR STUDENTS, TEAMS AND ORGANISATIONS"))
    a(("p", "A student or small team that experiments on Azure, for example with the free credit of Azure for Students, can "
            "exhaust the credit with a handful of forgotten resources and has no tool that explains why. An engineering manager needs "
            "to know which team owns a wasteful resource, and finance needs savings that are real rather than estimated. CloudPulse "
            "gives each of them a transparent view: every score, forecast and saving can be traced back to its evidence."))
    a(("h1", "1.3", "THE COST-TO-ACTION LOOP"))
    a(("p", "The core idea of the project is that every cost problem should travel through the same loop, from the first signal "
            "to a verified result:"))
    a(("num", [
        "Signal: on every sync CloudPulse reads the bill, inventory, metrics, recommendations and Activity Log.",
        "Context: each signal is priced per month using the actual billed cost where it exists and list prices otherwise.",
        "Finding: the signal becomes one de-duplicated, scored task with its evidence attached.",
        "Ownership: the creator found in the Activity Log (tags second) is matched to a user and the finding is assigned.",
        "Action: the owner starts work, fixes, dismisses with a reason or snoozes, with notifications and a full history.",
        "Verification: CloudPulse compares seven days of billed cost before and after the fix and records the real saving."]))
    a(("p", "If a fixed resource comes back, the finding reopens and its saving is withdrawn. CloudPulse only reads the cloud: it "
            "never creates, changes or deletes anything in an account."))
    a(("h1", "1.4", "OBJECTIVES AND SCOPE"))
    a(("bul", [
        "Collect cost, inventory, usage, recommendation and audit data from an Azure subscription with a least-privilege identity.",
        "Detect unattached disks, unused public IPs, orphaned snapshots, stopped-but-billed, idle and oversized virtual machines.",
        "Detect abnormal daily spend and forecast month-end spend and the day a budget will be exceeded.",
        "Attribute every resource to its creator and manage each finding through a role-controlled lifecycle.",
        "Count a saving only after billed cost confirms it, and withdraw it if the problem returns.",
        "Provide a reproducible Azure test environment and an automated test suite."]))
    a(("p", "Azure is the primary supported cloud. AWS and bills in the FinOps FOCUS open format are supported as optional inputs. "
            "Notifications are in-application only, and savings are limited to resource findings; anomalies, budget risks and "
            "tagging gaps are tracked but not counted as savings."))

    # ------------------------------------------------------------ CHAPTER 2
    a(("ch", 2, "LITERATURE REVIEW"))
    a(("p", "In this chapter, a review of existing work on cloud cost management, anomaly detection, forecasting and cloud security is "
            "presented. The review aims to give a contextual understanding of the practices, techniques and key components that "
            "shape the design of a cloud cost optimisation platform such as CloudPulse."))
    a(("h1", "2.1", "REVIEW OF CLOUD COST MANAGEMENT TOOLS"))
    a(("p", "Three families of tools are commonly used. Native consoles, such as Azure Cost Management, Azure Advisor and AWS Cost "
            "Explorer, are accurate and free, but each covers one provider and stops at reporting or at a generic recommendation [4]. "
            "Commercial FinOps platforms add multi-cloud views, allocation and dashboards, but they are closed products whose scoring "
            "methods are not visible and which generally need a paid subscription and broad access. Home-made scripts can list idle "
            "resources, but they give one-off reports with no workflow, history or verification."))
    a(("tbl", "Capability comparison of existing approaches and CloudPulse",
       ["Capability", "Native consoles", "Commercial tools", "Scripts", "CloudPulse"],
       [["Spend dashboards", "Yes", "Yes", "Rarely", "Yes"],
        ["Idle resource detection", "Partial", "Yes", "Partial", "Yes"],
        ["Creator from audit log", "Manual", "Varies", "No", "Automatic"],
        ["Task workflow", "No", "Varies", "No", "Yes"],
        ["Explainable priority score", "No", "Varies", "No", "Yes"],
        ["Saving verified on the bill", "No", "Rarely", "No", "Yes"],
        ["Read-only access", "n/a", "Varies", "Depends", "Yes"]],
       [4.6, 2.9, 3.2, 2.2, 3.2]))
    a(("h1", "2.2", "ADVANCEMENTS IN COST ANOMALY DETECTION AND FORECASTING"))
    a(("p", "Detecting unusual spend is an instance of the general anomaly detection problem, surveyed by Chandola, Banerjee and "
            "Kumar [5]. For daily cost series, robust statistics are preferred because spend is skewed and a single spike should not "
            "distort the baseline. The modified z-score based on the median absolute deviation, with the cut-off of 3.5 recommended by "
            "Iglewicz and Hoaglin [6], is simple, explainable and widely used. Weekly rhythm matters: spend usually differs between "
            "weekdays and weekends, so a good detector compares a day with the same weekday of earlier weeks."))
    a(("p", "For forecasting, exponential smoothing methods remain a strong baseline for short horizons. Holt's linear method "
            "extends simple smoothing with a trend term [7], and Hyndman and Athanasopoulos describe how seasonal factors and "
            "prediction intervals can be added [8]. These methods need no external machine-learning library, are interpretable and "
            "can be tuned by a small grid search, which suits a transparent cost tool."))
    a(("h1", "2.3", "COST PLATFORM DESIGN"))
    a(("p", "A cost optimisation platform has to combine several sources: billing data, an inventory of resources, usage metrics and "
            "an audit trail. Design considerations include how to price a finding (actual billed cost versus list price), how to "
            "avoid duplicate findings across repeated scans, how to rank findings of very different size, and how to verify a claimed "
            "saving. The FinOps cycle of inform, optimise and operate [3], [9] guides these choices: visibility first, then "
            "removal of waste, then continuous governance."))
    a(("h1", "2.4", "REVIEW OF THE MAJOR COMPONENTS USED"))
    a(("p", "Examining the system from a component perspective, the major elements are the identity layer, the data sources, the "
            "analytics and the storage and interface layers."))
    a(("bul", [
        "Identity: Microsoft Entra ID, service principals, role-based access control and OAuth 2.0 client-credentials tokens [10], [11].",
        "Data sources: Azure Cost Management, Azure Resource Graph, Azure Monitor metrics, the Activity Log, Azure Advisor and the "
        "public Retail Prices API [12].",
        "Analytics: robust z-score, Holt smoothing, percentile rules and a logarithmic priority score.",
        "Storage and interface: SQLAlchemy over SQLite or PostgreSQL, a FastAPI service and a single-page JavaScript interface."]))
    a(("h1", "2.5", "APPLICATIONS OF CLOUD COST OPTIMISATION"))
    a(("p", "Cost optimisation tools are applied in student and training environments to stop credits being consumed by forgotten "
            "resources, in start-ups to keep the monthly bill predictable, in enterprises to allocate spend to teams, and in "
            "managed-service providers to report verified savings to customers. Reducing idle infrastructure also reduces the "
            "energy consumed by data centres, which links cost control with sustainability."))
    a(("h1", "2.6", "CHALLENGES IN CLOUD COST OPTIMISATION"))
    a(("p", "Several challenges are reported in practice. Billing data arrives with a delay of hours, so savings cannot be confirmed "
            "immediately. Resource tags are often missing, so the owner is unknown. Memory utilisation of virtual machines is not "
            "available without an agent, which limits right-sizing advice. Tools that request broad write permissions are risky to "
            "connect to production accounts, and many tools hide how their scores are produced [4], [9]."))
    a(("h1", "2.7", "CONCLUSION"))
    a(("p", "The literature review shows that cost visibility is widely available but that owner attribution, prioritisation and "
            "verified savings are rarely combined in one transparent, read-only tool. This gap is addressed by the design and "
            "development of CloudPulse in the following chapters."))

    # ------------------------------------------------------------ CHAPTER 3
    a(("ch", 3, "SYSTEM FUNCTIONALITY"))
    a(("p", "CloudPulse is a three-tier web application: a browser interface, one Python server that contains the API, the "
            "scheduler and the analytics, and a SQL database. Azure is an external system that is only read. Figure 3.1, on the "
            "next page, shows all components and the numbered flows, including the Azure credential path."))
    a(("figrot", "assets/fig_architecture.png", "CloudPulse system architecture with the Azure credential and data flows"))
    a(("h1", "3.1", "COST DATA COLLECTION"))
    a(("p", "The CloudPulse system performs one synchronisation by a single function that is run by a scheduler every six hours "
            "or by the Sync button (Figure 3.2). It signs in to Azure, reads the bill with the Cost Management query API, lists the "
            "inventory with Azure Resource Graph, reads 14 days of virtual machine metrics from Azure Monitor and cost "
            "recommendations from Azure Advisor, finds the creator of each resource in the Activity Log, and prices every "
            "signal. Each step records its own error, so a permission problem with one source does not stop the others."))
    a(("fig", "assets/fig_pipeline.png", "The synchronisation pipeline executed on every sync", 10.8))
    a(("h2", "3.1.1", "AZURE CREDENTIALS"))
    a(("p", "Everything CloudPulse knows about a subscription comes through one identity. An app registration with a service "
            "principal is created in the Microsoft Entra ID tenant; it has a client ID and a client secret and is granted the "
            "Reader and Cost Management Reader roles on the subscription only. CloudPulse exchanges the tenant ID, client ID and "
            "secret for a short-lived access token and sends it as a Bearer token with every read request. When the application runs "
            "on Azure App Service, a managed identity is used and no secret exists. A secret entered in the interface is "
            "encrypted with Fernet and is never returned by the API."))
    a(("fig", "assets/fig_credflow.png", "Azure credential creation, token acquisition and read-only request sequence", 10.2))
    a(("h1", "3.2", "DATA PROCESSING AND DETECTION"))
    a(("p", "The heart of the system lies in the analytics layer, which converts raw data into findings. Table 3.1 lists the waste "
            "detection rules. Where Cost Management already reports the billed cost of a resource, the actual cost replaces the "
            "list-price estimate."))
    a(("tbl", "Waste detection rules applied to the Azure inventory",
       ["Finding", "Rule", "Monthly impact", "Confidence"],
       [["Unattached disk", "diskState = Unattached", "Size x disk tier price", "0.95"],
        ["Idle public IP", "Static, no IP configuration, no NAT gateway", "Public IP price", "0.95"],
        ["Orphaned snapshot", "Source disk deleted, or older than 30 days", "Size x snapshot price", "0.90 / 0.60"],
        ["VM stopped but billed", "Power state stopped (not deallocated)", "Compute hours x price + disks", "0.90"],
        ["Idle VM", "p95 CPU < 5% and network < 5 MB per hour", "Compute price of the size", "0.85"],
        ["Oversized VM", "p95 CPU < 20% and peak CPU < 80%", "Price difference to smaller size", "0.70"]],
       [3.4, 5.6, 4.6, 2.5]))
    a(("p", "Spend anomalies use a weekday-aware robust z-score: a day is flagged when z = (x - median) / (1.4826 x MAD) is above "
            "3.5 against the same weekday of the previous four weeks and the excess is at least 20% of the usual cost. Month-end "
            "spend is forecast with Holt's linear smoothing, weekday factors and an 80% range, and a budget risk is raised when the "
            "forecast passes the budget. Every finding receives a priority score:"))
    a(("p", "score = 100 x (0.6 x impact score + 0.4 x severity weight) x confidence x age factor, where the impact score is "
            "log10(1 + impact) / log10(1 + 1000). Scores of 70 and above are P1, 45 and above P2, 25 and above P3, otherwise P4. "
            "For example a stopped VM costing $70.08 a month with confidence 0.9 scores 53 (P2), and 69 after 30 days open."))
    a(("fig", "assets/fig_priority.png", "Priority score against monthly impact (confidence 0.9, new finding)", 11.0))
    a(("h1", "3.3", "DISPLAY AND USER INTERFACE"))
    a(("p", "CloudPulse has a user-friendly browser interface with ten pages: Overview, Cost explorer, Anomalies, Budgets, "
            "Findings, Owners, Savings, Data sources and, for administrators, Workspaces and users and the Audit log. The interface "
            "is drawn with plain HTML, CSS and JavaScript and SVG charts, supports light and dark themes and works from 400 pixel "
            "phones to wide desktops. The pages are described with screenshots in Chapter 5."))
    a(("h1", "3.4", "DATA LOGGING AND FINDING LIFECYCLE"))
    a(("p", "To support review and accountability, CloudPulse logs every action. Each finding keeps its own event history, sign-ins "
            "and administrative changes are written to an audit log, and daily costs are stored per service and per resource for "
            "verification. A finding moves through the states shown in Figure 3.3."))
    a(("fig", "assets/fig_lifecycle.png", "Finding lifecycle, with automatic and manual transitions", 12.0))
    a(("p", "Administrators and workspace owners may perform every action, the assignee may start and resolve, and viewers can only "
            "read. Dismissing needs a written reason and snoozing is limited to 1 to 90 days. Verification compares the average "
            "daily cost of the resource in the 7 days before the fix with the days after it and needs at least 3 billed days; the "
            "realised saving is the drop multiplied by 30.4 days."))
    a(("h1", "3.5", "APPLICATIONS"))
    a(("p", "The CloudPulse system finds applications in various domains:"))
    a(("num", [
        "Student and Training Labs: it prevents free credits from being consumed by forgotten resources.",
        "Small Teams and Start-ups: it keeps the monthly bill predictable and flags budget breaches early.",
        "Enterprise FinOps: it assigns waste to the teams that created it and reports verified savings.",
        "Security and Governance: it highlights untagged spend and unknown owners, and keeps an audit trail."]))

    # ------------------------------------------------------------ CHAPTER 4
    a(("ch", 4, "TEST AND IMPLEMENTATION"))
    a(("h1", "4.1", "TEST PLAN"))
    a(("p", "The algorithms were written as pure Python functions whose expected values were calculated by hand, then the Azure "
            "collector was tested against a fake cloud, then the findings engine and API, and finally the interface. A scripted Azure "
            "workload was used so that the same code could be proven on a real subscription."))
    a(("h2", "4.1.1", "DETECTION RULE AND ALGORITHM VALIDATION"))
    a(("obj", "Objective", "Verify that the anomaly, forecast, priority, VM verdict and verification algorithms give hand-computed values."))
    a(("obj", "Procedure", ""))
    a(("bul", ["Write 23 unit tests with expected values calculated by hand.",
               "Test flat series, spikes with weekday baseline, ongoing spikes, small increases and short histories.",
               "Test forecasts for complete, constant, linear and short series, and priority values and bands."]))
    a(("obj", "Results", "All 23 algorithm tests passed; values matched the hand calculations."))
    a(("h2", "4.1.2", "AZURE COLLECTOR INTEGRATION"))
    a(("obj", "Objective", "Verify the complete loop from sync to verified saving, including permissions and regressions."))
    a(("obj", "Procedure", ""))
    a(("bul", ["Run a full-loop test against a fake Azure cloud: sync, findings, owners, assign, start, dismiss, resolve, verify.",
               "Check that a viewer may resolve their own finding but not dismiss another's.",
               "Make a fixed resource reappear and check that the finding reopens and the saving is withdrawn."]))
    a(("obj", "Results", "The integration test passed, including the reappearing-resource regression and the audit trail."))
    a(("h2", "4.1.3", "USER INTERFACE TESTING"))
    a(("obj", "Objective", "Evaluate clarity and functionality of every page at desktop and phone width."))
    a(("obj", "Procedure", ""))
    a(("bul", ["Load all nine pages in headless Chromium at 1280 and 400 pixels and watch the browser console.",
               "Check that figures agree across pages and that tooltips and filters work."]))
    a(("obj", "Results", "No console errors. The review found a mistyped colour value that made the main text almost "
                         "transparent; it was fixed and a regression test was added."))
    a(("h2", "4.1.4", "AZURE CONNECTIVITY TESTING"))
    a(("obj", "Objective", "Test sign-in and read access to a real subscription."))
    a(("obj", "Procedure", ""))
    a(("bul", ["Create the read-only identity and run python -m app.manage check-azure.",
               "Plant four wasted resources with the Azure scripts and run a sync."]))
    a(("obj", "Results", "The command reports Connected with the subscription name, or the exact reason for failure; "
                         "planted resources are reported as findings with the creator from the Activity Log."))
    a(("tbl", "Automated tests (27)",
       ["File", "Tests", "What is verified"],
       [["tests/test_analytics.py", "23", "Statistics helpers, anomaly, forecast, priority, VM verdict, before/after verification"],
        ["tests/test_engine.py", "1", "Full loop on a fake Azure cloud, permissions, regression, audit trail"],
        ["tests/test_static.py", "3", "CSS colour tokens, page renderers, Azure setup diagnostics"]],
       [4.4, 1.6, 10.0]))
    a(("h1", "4.2", "IMPLEMENTATION CHALLENGES"))
    a(("h2", "4.2.1", "DELAYED BILLING DATA"))
    a(("obj", "Challenge", "Azure publishes cost data 8 to 24 hours after usage."))
    a(("obj", "Solution", "Verification waits for 3 billed days after a fix, and a fixed clock makes the demonstration reproducible."))
    a(("h2", "4.2.2", "UNKNOWN RESOURCE OWNERS"))
    a(("obj", "Challenge", "Resources are often created without owner tags."))
    a(("obj", "Solution", "Read the earliest successful write in the Activity Log; treat GUID callers as service identities."))
    a(("h2", "4.2.3", "CREDENTIAL HANDLING"))
    a(("obj", "Challenge", "A monitoring tool must not become a security risk."))
    a(("obj", "Solution", "Read-only roles, Fernet-encrypted secrets, a managed identity option and a start-up diagnostic that explains missing settings."))
    a(("h1", "4.3", "LESSONS LEARNED"))
    a(("bul", ["Billing delay must be designed for, not worked around.",
               "Audit logs are a more reliable source of ownership than tags.",
               "Least privilege and clear failure messages make a tool safe and easy to adopt."]))
    a(("h1", "4.4", "CONCLUSION"))
    a(("p", "Testing and implementation confirm that CloudPulse detects wasted spend, attributes it to owners and verifies savings "
            "on the bill, while addressing the challenges of delayed data, missing tags and credential safety."))

    # ------------------------------------------------------------ CHAPTER 5
    a(("ch", 5, "RESULTS AND DISCUSSION"))
    a(("p", "The screenshots in this chapter were taken from the running application in its demonstration workspace, which runs "
            "the same collection, detection, scoring and verification code as a live Azure workspace on a bundled FinOps FOCUS "
            "sample bill (1,166 daily rows from 21 March to 30 September 2024)."))
    a(("h1", "5.1", "DETECTION RULE VALIDATION"))
    a(("h2", "5.1.1", "VALIDATION RESULTS"))
    a(("p", "All 23 algorithm tests passed. In the demonstration workspace the system produced twelve findings, listed in Table 5.1 "
            "in order of priority score. The budget risk and the large idle virtual machines outrank small idle IP addresses, and a "
            "verified item keeps its original score."))
    a(("tbl", "Findings in the demo workspace (impact in USD per month)",
       ["No.", "Finding", "Cloud", "Impact", "Score", "Status"],
       [["1", "September 2024 ended 9% over budget", "-", "230.00", "75 (P1)", "Open"],
        ["2", "VM gpu-trial-01 is stopped but still billed", "Azure", "70.08", "69 (P2)", "In progress"],
        ["3", "VM reporting-vm runs but does almost nothing", "Azure", "70.08", "65 (P2)", "Open"],
        ["4", "Spend on 24 Sep was 2.3x the usual", "AWS", "2,909.55", "65 (P2)", "Resolved"],
        ["5", "VM api-prod-01 is larger than it needs to be", "Azure", "70.08", "54 (P2)", "Open"],
        ["6", "Advisor: reserved instances", "Azure", "41.50", "50 (P2)", "Open"],
        ["7", "Disk web-01_OsDisk_old attached to nothing", "Azure", "19.71", "43 (P3)", "Verified"],
        ["8", "EBS volume db-backup-old attached to nothing", "AWS", "16.00", "39 (P3)", "Verified"],
        ["9", "EC2 instance load-test-runner is stopped", "AWS", "8.00", "36 (P3)", "Open"],
        ["10", "Public IP staging-lb-ip points at nothing", "Azure", "3.65", "31 (P3)", "Dismissed"],
        ["11", "Elastic IP 13.232.81.40 attached to nothing", "AWS", "3.60", "31 (P3)", "Snoozed"],
        ["12", "Snapshot pre-upgrade-snap not needed", "Azure", "3.20", "29 (P3)", "Open"]],
       [1.0, 6.4, 1.6, 1.9, 2.3, 2.5]))
    a(("h2", "5.1.2", "IMPLICATIONS"))
    a(("p", "A single explainable score lets a team decide what to fix first without arguing about units. The logarithmic impact "
            "term prevents one very large item from hiding all others, and the age factor gradually raises forgotten findings."))
    a(("h1", "5.2", "AZURE COLLECTOR INTEGRATION"))
    a(("h2", "5.2.1", "INTEGRATION RESULTS"))
    a(("p", "The full-loop test passed on the fake Azure cloud. Only findings that reach the verified state contribute to savings. In "
            "the demonstration two resources were fixed and then confirmed by the before and after comparison (Table 5.2): the "
            "estimate was $35.71 a month and the realised saving $33.44 a month, an accuracy of 93.6%."))
    a(("tbl", "Verified savings in the demo workspace",
       ["Resource", "Cloud", "Estimated (USD/month)", "Realised (USD/month)", "Accuracy"],
       [["Disk web-01_OsDisk_old", "Azure", "19.71", "18.24", "92.5%"],
        ["EBS volume db-backup-old", "AWS", "16.00", "15.20", "95.0%"],
        ["Total", "", "35.71", "33.44", "93.6%"]],
       [5.0, 1.8, 3.4, 3.4, 2.1]))
    a(("h2", "5.2.2", "IMPLICATIONS"))
    a(("p", "Verification against the bill replaces self-reported savings. It also shows that estimates are slightly optimistic, "
            "information that a plain report would never provide."))
    a(("h1", "5.3", "USER INTERFACE TESTING"))
    a(("h2", "5.3.1", "USER INTERFACE RESULTS"))
    a(("p", "The user interface testing evaluated the clarity and functionality of the pages. The screenshots below show the "
            "sign-in page and the four main analysis pages."))
    a(("fig", "assets/shot_login.png", "CloudPulse sign-in page", 15.0))
    a(("p", "Figure 5.1 is the entry point. Users sign in with the account created by the administrator, or press Explore the "
            "demo for a read-only sample workspace. The right-hand panel states the value of the product with live figures: $123.73 "
            "a month is going to 7 idle resources and CloudPulse traced who created 6 of them, with examples such as the stopped VM "
            "gpu-trial-01 ($70.08), the unattached volume db-backup-old ($16.00) and the stopped instance load-test-runner ($8.00)."))
    a(("fig", "assets/shot_overview.png", "Overview page (administrator view of the demo workspace)", 15.0))
    a(("p", "Figure 5.2 answers what was spent, what needs fixing and what fixing has saved. Spend for the month was $2,829.99, "
            "109% of the $2,600 budget. Six findings worth $262.94 a month are waiting to be fixed, and verified fixes have already "
            "cut $33.44 a month with estimates 94% accurate. The loop panel shows 5 open findings ($192.86), 1 owned ($70.08), "
            "0 fixed and being checked and 2 verified ($33.44)."))
    a(("fig", "assets/shot_costs.png", "Cost explorer with the daily tooltip for 18 September 2024", 15.0))
    a(("p", "Figure 5.3 breaks spend down by service or provider: total $2,829.99, 80 services billed, daily average $94.33, with "
            "Amazon Elastic Compute Cloud the largest service. The tooltip for 18 September 2024 lists each service's cost, adding "
            "up to $201.95. The sample bill mixes AWS and Azure services, showing the multi-provider normalisation of the FOCUS format."))
    a(("fig", "assets/shot_anomalies.png", "Anomalies page showing the flagged day 24 September 2024", 15.0))
    a(("p", "Figure 5.4 shows the anomaly detector's output: one anomaly with an excess of $95.71. On 24 September 2024 the day cost "
            "$169.26 against a usual $73.55 (z-score 7.9), and Amazon Elastic Compute Cloud explains 99.1% of the increase. The "
            "spike is still running high, so it is not yet verified as back to normal on the bill."))
    a(("fig", "assets/shot_budgets.png", "Budgets page with the cumulative spend line and the budget breach marker", 15.0))
    a(("p", "Figure 5.5 compares the month with a $2,600 budget. The budget was passed on 28 September 2024 and the month ended at "
            "$2,829.99, which is $229.99 over. For a month in progress the chart also shows the forecast and its 80% range."))
    a(("h2", "5.3.2", "IMPLICATIONS"))
    a(("p", "The figures agree across every page, which makes the interface trustworthy: the open and owned values on the Overview "
            "add up to the $262.94 waiting to be fixed, and the budget page agrees with the monthly total."))
    a(("h1", "5.4", "AZURE CONNECTIVITY"))
    a(("h2", "5.4.1", "CONNECTIVITY RESULTS"))
    a(("p", "The check-azure command and the connection test in the administrator page report either Connected with the "
            "subscription name or the exact reason for failure: no Reader role (403), subscription not found (404) or sign-in "
            "failed. A live subscription is validated with the scripted workload and the four planted wasted resources."))
    a(("h2", "5.4.2", "IMPLICATIONS"))
    a(("p", "Clear diagnostics make a read-only identity easy to set up and troubleshoot, which is important for adoption. Cost "
            "charts need Azure's billing data, which arrives 8 to 24 hours after usage, while waste findings and owners appear "
            "within minutes."))
    a(("h1", "5.5", "IMPLEMENTATION CHALLENGES"))
    a(("h2", "5.5.1", "DELAYED BILLING DATA"))
    a(("p", "The delay of billing data was handled by waiting for three billed days before verifying a fix, so a saving is never "
            "claimed from incomplete data."))
    a(("h2", "5.5.2", "UNKNOWN RESOURCE OWNERS"))
    a(("p", "Owners are taken from the Activity Log first and from tags second, and the answer is cached. Owners are known for "
            "resources created in the last 89 days unless a tag exists."))
    a(("h2", "5.5.3", "CREDENTIAL HANDLING"))
    a(("p", "Credentials are protected by least privilege, encryption at rest and a managed identity option, and the application "
            "uses scrypt password hashes, server-side sessions, a CSRF header and a login rate limit."))
    a(("h1", "5.6", "LESSONS LEARNED"))
    a(("p", "The implementation and testing phase provided valuable insights into the operation of a cloud cost platform."))
    a(("bul", ["Billing delay must be planned for in every verification step.",
               "Explainable algorithms are easier to test, trust and defend than opaque scores.",
               "Visual review in a real browser catches defects that unit tests cannot."]))

    # ------------------------------------------------------------ CHAPTER 6
    a(("ch", 6, "CONCLUSION AND FUTURE SCOPE"))
    a(("h1", "6.1", "CONCLUSION"))
    a(("p", "In conclusion, CloudPulse proves to be a valuable and practical platform for controlling cloud spend. It reads an "
            "Azure subscription with a least-privilege, read-only identity, detects idle and wasted resources, flags anomalies and "
            "forecasts budget breaches, assigns every finding to the person who created the resource and counts a saving only "
            "after the bill confirms it. Transparent algorithms make every figure explainable, and 27 automated tests with a "
            "scripted Azure environment support the results. In the demonstration workspace the system reported $262.94 a month "
            "of open waste and $33.44 a month of verified savings at 94% estimate accuracy, and aligns with the growing emphasis "
            "on FinOps and sustainable use of cloud resources."))
    a(("h1", "6.2", "FUTURE SCOPE"))
    a(("p", "The platform holds substantial promise for education, small teams and enterprises. Its utility extends beyond the "
            "current capabilities, and future developments include:"))
    a(("bul", [
        "Enhanced alerts: e-mail, Microsoft Teams and Slack notifications in addition to the in-app inbox.",
        "Sign-in with Microsoft Entra ID (OpenID Connect) so organisations can use existing accounts.",
        "Google Cloud collector and deeper AWS coverage such as idle load balancers and unused NAT gateways.",
        "Reservation and savings-plan analysis with purchase recommendations.",
        "Tag-compliance policies, and showback or chargeback reports by team.",
        "Approval-gated remediation, for example deallocating a stopped VM after the owner confirms.",
        "PostgreSQL as the default store with a shared job queue for multi-instance deployment.",
        "Memory and disk metrics through the Azure Monitor agent for more accurate right-sizing."]))
    a(("h1", "6.3", "REFERENCES"))
    return B


ABBREV = [("API", "Application Programming Interface"), ("ARM", "Azure Resource Manager"), ("AWS", "Amazon Web Services"),
          ("CLI", "Command-Line Interface"), ("CSS", "Cascading Style Sheets"), ("CSRF", "Cross-Site Request Forgery"),
          ("CSV", "Comma-Separated Values"), ("FinOps", "Cloud Financial Operations"),
          ("FOCUS", "FinOps Open Cost and Usage Specification"), ("HTML", "HyperText Markup Language"),
          ("IAM", "Identity and Access Management"), ("IP", "Internet Protocol"), ("JSON", "JavaScript Object Notation"),
          ("JWT", "JSON Web Token"), ("MAD", "Median Absolute Deviation"), ("ORM", "Object-Relational Mapper"),
          ("RBAC", "Role-Based Access Control"), ("REST", "Representational State Transfer"), ("SQL", "Structured Query Language"),
          ("SVG", "Scalable Vector Graphics"), ("UI", "User Interface"), ("VM", "Virtual Machine")]

REFS = [
    "M. Armbrust et al., “A view of cloud computing,” Communications of the ACM, vol. 53, no. 4, pp. 50-58, 2010.",
    "P. Mell and T. Grance, “The NIST definition of cloud computing,” NIST Special Publication 800-145, 2011.",
    "FinOps Foundation, “What is FinOps?” https://www.finops.org/introduction/what-is-finops/",
    "Microsoft, “Azure Cost Management and Billing documentation,” Microsoft Learn. https://learn.microsoft.com/azure/cost-management-billing/",
    "V. Chandola, A. Banerjee and V. Kumar, “Anomaly detection: A survey,” ACM Computing Surveys, vol. 41, no. 3, 2009.",
    "B. Iglewicz and D. C. Hoaglin, How to Detect and Handle Outliers, ASQC Quality Press, 1993.",
    "C. C. Holt, “Forecasting seasonals and trends by exponentially weighted moving averages,” International Journal of Forecasting, vol. 20, no. 1, pp. 5-10, 2004.",
    "R. J. Hyndman and G. Athanasopoulos, Forecasting: Principles and Practice, 3rd ed., OTexts, 2021. https://otexts.com/fpp3/",
    "J. R. Storment and M. Fuller, Cloud FinOps, 2nd ed., O'Reilly Media, 2023.",
    "D. Hardt, Ed., “The OAuth 2.0 authorization framework,” RFC 6749, IETF, 2012.",
    "Microsoft, “Azure built-in roles,” Microsoft Learn. https://learn.microsoft.com/azure/role-based-access-control/built-in-roles",
    "Microsoft, “Azure Resource Manager REST API reference,” Microsoft Learn. https://learn.microsoft.com/rest/api/azure/",
    "C. Percival and S. Josefsson, “The scrypt password-based key derivation function,” RFC 7914, IETF, 2016.",
    "S. Ramirez, “FastAPI documentation.” https://fastapi.tiangolo.com/",
    "SQLAlchemy Project, “SQLAlchemy 2.0 documentation.” https://docs.sqlalchemy.org/",
]
