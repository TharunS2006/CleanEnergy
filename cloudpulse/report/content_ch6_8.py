"""Chapters 6-8: Results, Conclusion, References."""
A = "assets/"

FINDINGS = [  # from the running demo workspace (score, impact and status as stored by the application)
    ["1", "September 2024 ended 9% over budget", "Budget risk", "-", "230.00", "75 (P1)", "Open"],
    ["2", "VM gpu-trial-01 is stopped but still billed", "Idle resource", "Azure", "70.08", "69 (P2)", "In progress"],
    ["3", "VM reporting-vm runs but does almost nothing", "Idle VM", "Azure", "70.08", "65 (P2)", "Open"],
    ["4", "Spend on 24 Sep was 2.3x the usual", "Spend anomaly", "AWS", "2,909.55*", "65 (P2)", "Resolved (checking)"],
    ["5", "VM api-prod-01 is larger than it needs to be", "Oversized VM", "Azure", "70.08", "54 (P2)", "Open"],
    ["6", "Advisor: reserved instances to save over pay-as-you-go", "Advisor", "Azure", "41.50", "50 (P2)", "Open"],
    ["7", "Disk web-01_OsDisk_old is attached to nothing", "Idle resource", "Azure", "19.71", "43 (P3)", "Verified"],
    ["8", "EBS volume db-backup-old is attached to nothing", "Idle resource", "AWS", "16.00", "39 (P3)", "Verified"],
    ["9", "EC2 instance load-test-runner is stopped; volumes still bill", "Idle resource", "AWS", "8.00", "36 (P3)", "Open"],
    ["10", "Public IP staging-lb-ip points at nothing", "Idle resource", "Azure", "3.65", "31 (P3)", "Dismissed"],
    ["11", "Elastic IP 13.232.81.40 is attached to nothing", "Idle resource", "AWS", "3.60", "31 (P3)", "Snoozed"],
    ["12", "Snapshot pre-upgrade-snap is no longer needed", "Idle resource", "Azure", "3.20", "29 (P3)", "Open"],
]


def chapter6(r):
    r.h(1, "6. RESULTS")
    r.para("This chapter presents the running system. The five screenshots were taken from the application served at "
           "`127.0.0.1:8000` in a desktop browser with the dark theme, which the interface selects automatically from the "
           "operating-system preference. They show the sign-in page and the four main analysis pages. All figures that "
           "appear in the screenshots come from the application's built-in demonstration workspace, which runs the same "
           "collection, detection, scoring and verification code as a live Azure workspace on the bundled FOCUS sample bill.")
    r.h(2, "6.1  Experimental Set-up")
    r.table("Table 6.1: Set-up used for the results in this chapter",
            ["Item", "Value"],
            [["Application", "CloudPulse v5 served by Uvicorn on 127.0.0.1:8000, SQLite database"],
             ["Data", "FOCUS sample bill (100,000 records) aggregated to 1,166 daily rows, 21 March to 30 September 2024; "
              "12 example findings with scripted owners and history"],
             ["Clock", "The demonstration fixes its \"today\" at 1 October 2024 so that the figures are reproducible"],
             ["Accounts", "Administrator (Overview screenshot) and read-only demo visitor (the other pages)"],
             ["Browser", "Desktop Chrome, 1920 × 1080; interface verified in headless Chromium at 400 px as well"],
             ["Tests", "pytest, 27 passed"]],
            widths=[3.2, 11.8], size=10.5)

    r.h(2, "6.2  Sign-in Page")
    r.figure(A + "shot_login.png", "Figure 6.1: CloudPulse sign-in page (127.0.0.1:8000/login)", width_cm=15.0)
    r.para("Figure 6.1 is the entry point of the system. The left half contains the **Email** and **Password** fields, a "
           "**Show** switch for the password, the blue **Sign in** button and a second, outlined button, **Explore the demo**. "
           "Signing in uses the account the CloudPulse administrator created; there is deliberately no self-registration, and "
           "the note at the bottom, \"Forgot your password? Ask your CloudPulse administrator to reset it\", reflects that the "
           "administrator resets passwords with a temporary one that must be changed at first use. **Explore the demo** opens the "
           "read-only sample workspace without any account, which is the mode used for faculty and visitor demonstrations "
           "and for all other screenshots; the grey note under the button states that it uses the FinOps Foundation's sample bill "
           "and example resources.")
    r.para("The right half states what the product does with live examples computed by the application: \"**$123.73 a month** is "
           "going to **7 idle resources**, and CloudPulse traced who created **6 of them**.\" Three rows illustrate it. "
           "**gpu-trial-01**, a virtual machine that is *stopped, still billed*, costs $70.08 a month and is attributed to the "
           "person with initials AK; **db-backup-old**, an EBS volume *attached to nothing*, costs $16.00; **load-test-runner**, "
           "an EC2 instance that is *stopped* while its *disks still bill*, costs $8.00. The coloured circles are the "
           "creators found from audit logs. The three bullets summarise the capabilities delivered in this report: spend "
           "across Azure and AWS day by day, idle resources priced, and the creator of each one found from audit logs "
           "without needing tags. This page therefore demonstrates the authentication feature (FR1) and the product's "
           "value proposition in one view.")

    r.h(2, "6.3  Overview Page")
    r.figure(A + "shot_overview.png", "Figure 6.2: Overview page (administrator view of the demo workspace)", width_cm=15.0)
    r.para("The Overview page, Figure 6.2, is the first page after sign-in and answers three questions at once: what was spent, "
           "what needs fixing, and what has fixing already saved. The **left navigation** is grouped into *Monitor* "
           "(Overview, Cost explorer, Anomalies, Budgets), *Act* (Findings with a badge of **7** items still to do, Owners, Savings), "
           "*Setup* (Data sources) and, because the screenshot was taken as administrator, *Administration* (Workspaces & users, "
           "Audit log). The footer of the sidebar shows the data source (\"Demo data\") and when it last synchronised, and the signed-in user. "
           "In the top bar are the provider filter (**All providers**), the range selector **7D / 30D / 90D**, the notification "
           "bell and the blue **Sync** button, which is visible only to users who may start a collection. The amber banner reminds "
           "the viewer that the data is sample data.")
    r.para("The large sentence is generated from the numbers below it: \"You spent **$2,829.99** between 1 Sept and 30 Sept. "
           "**6 findings** worth **$262.94 a month** are waiting to be fixed, and fixes have already cut **$33.44 a month** off the "
           "bill.\" The four cards repeat the figures with context. **Spend, last 30 days** is $2,829.99. "
           "**Total for September 2024** is also $2,829.99, drawn against the budget as a red bar, \"109% of $2,600, over on "
           "28 Sept\". **Waiting to be fixed** is $262.94 a month made of 6 findings plus 1 governance finding. **Verified savings** "
           "is $33.44 a month, of which $11.80 has already been saved to date, and \"estimates 94% accurate\", meaning the realised "
           "saving divided by the original estimate.")
    r.para("The panel **From finding to verified saving** displays the whole loop as four stages with the monthly value of each: "
           "**Open** 5 findings ($192.86), **Owned** 1 ($70.08), **Fixed, checking** 0 ($0.00) and **Verified** 2 ($33.44). "
           "The open and owned values add up to the $262.94 shown above, which is a useful consistency check between cards. "
           "The strip below lists items that are tracked but not counted as savings: one dismissed with a reason, one snoozed, "
           "one anomaly being tracked and one governance finding. This single screen therefore evidences the signal-to-"
           "verification loop (FR5, FR8, FR9) and the budget forecast (FR7).")

    r.h(2, "6.4  Cost Explorer")
    r.figure(A + "shot_costs.png", "Figure 6.3: Cost explorer with the daily tooltip for 18 September 2024", width_cm=15.0)
    r.para("The Cost explorer, Figure 6.3, breaks the bill down by service or provider. The four cards report **Total** "
           "$2,829.99 for 1 to 30 September 2024, **Previous 30 days** shown as a dash because the sample contains no billing data "
           "for that comparison period, **Services billed** 80 with the largest being *Amazon Elastic Compute Cloud*, and "
           "**Daily average** $94.33, which is the total divided by 30 days. The card values are consistent with the Overview.")
    r.para("The chart **Spend by service** draws one stacked bar per day with the top five services in distinct colours and "
           "everything else grouped as *Other*; the **Service / Provider** switch at the right changes the grouping. The legend "
           "shows the 30-day totals: Amazon Elastic Compute Cloud $1,757, Virtual Machines $199, Azure SQL Database $159, SQL "
           "Database and others, and Other $525. In this screenshot the pointer is on **18 September 2024**, and the tooltip "
           "lists that day's cost per service: Amazon Elastic Compute Cloud $96.95, Virtual Machines $6.52, Azure SQL Database "
           "$38.80, SQL Database $41.59, Amazon Relational Database Service $3.77 and Other $14.32, giving a **total of $201.95**. "
           "The sample bill mixes AWS and Azure services, which demonstrates the multi-provider normalisation done by the FOCUS "
           "format. This page covers FR3 and FR10: reading daily cost by service and importing bills in the FOCUS format.")

    r.h(2, "6.5  Anomalies Page")
    r.figure(A + "shot_anomalies.png", "Figure 6.4: Anomalies page showing the flagged day 24 September 2024", width_cm=15.0)
    r.para("Figure 6.4 shows the anomaly detector's output. The summary cards state that **1 anomaly** is tracked (0 still open, "
           "because its finding has already been marked as fixed), that the **excess on those days** is **$95.71** above the "
           "usual cost for each day, that **1** anomaly is **still running high** (\"cost hasn't come back down\") and that **0** are "
           "**back to normal, verified on the bill**. The last card is what keeps CloudPulse honest: marking an anomaly as fixed "
           "is not enough, the bill has to return to normal for three billed days.")
    r.para("The chart **Last 90 days** draws daily spend as bars with a dashed average line; \"Ringed days were flagged. Click a day "
           "with a ring to open it.\" The ringed bar is **24 September 2024**, and the tooltip reads **Total $169.26**, "
           "**Unusual spike**. Following the method of Section 5.6, the same weekday of the previous weeks had a median of $73.55, so "
           "the excess is $95.71 or 2.3 times the usual cost, with a robust z-score of 7.9 (the threshold is 3.5). The next two days "
           "also stayed high, so the spike was classified as *ongoing* and its monthly impact projected as $2,909.55 in the findings "
           "list. Opening the day lists the services that caused the increase: Amazon Elastic Compute Cloud accounts for 99.1 % "
           "of it, rising from a usual $19.04 to $164.14. Below the chart, the section **How a day gets flagged** explains the rule "
           "in plain language. Other tall days are not ringed when they fail the rule against their own weekday baseline, "
           "for example 18 September ($201.95 in Figure 6.3), "
           "which keeps false alarms low. This page demonstrates FR7.")

    r.h(2, "6.6  Budgets Page")
    r.figure(A + "shot_budgets.png", "Figure 6.5: Budgets page with the cumulative spend line and the budget breach marker", width_cm=15.0)
    r.para("The Budgets page, Figure 6.5, compares the month with a limit that the workspace owner sets. The four cards show "
           "the **Budget** $2,600 for September 2024, **Spent so far** $2,829.99 (109 % of budget), **Month total** $2,829.99 "
           "(\"Month complete\") and **Over by** $229.99 in red, with the note \"passes the budget on 28 Sept 2024\". The chart "
           "**September 2024, day by day** shows the cumulative spend as a blue line and area, the budget as a dashed horizontal "
           "line labelled \"Budget $2.6k\", and a vertical red marker labelled **Over budget 28 Sept** where the line crosses. "
           "The tooltip for **17 September 2024** reads \"Spent so far $1,368.20; That day $81.71; Budget left $1,231.80\", and "
           "$2,600 − $1,368.20 = $1,231.80 confirms the arithmetic.")
    r.para("Because the demonstration month is already complete, the forecast equals the actual total and the uncertainty band "
           "collapses to a line. For a month in progress the same chart extends the line with the Holt forecast and an 80 % "
           "shaded band, and the breach marker moves to the *predicted* day. The panel below the chart, **How the forecast is "
           "made**, documents the method for the reader. The corresponding **Budget risk** finding is the highest ranked "
           "item in the system with a score of 75 (P1), which links this page to the findings workflow.")

    r.h(2, "6.7  Findings Produced and Their Priority")
    r.para("Table 6.2 lists the twelve findings of the demonstration workspace in order of priority score, as stored by the "
           "application. The ordering shows the scoring at work: the budget risk and the large idle virtual machines outrank small "
           "idle IP addresses, and a verified item keeps its original score.")
    r.table("Table 6.2: Findings in the demo workspace (impact in USD per month)",
            ["#", "Finding", "Kind", "Cloud", "Impact", "Score", "Status"],
            FINDINGS, widths=[0.8, 5.8, 2.3, 1.3, 1.7, 1.7, 2.3], size=9)
    r.para("* An ongoing anomaly is projected as excess × 30.4 days; it is an investigation and is not counted as a saving.", size=10,
           italic=True, spacing=1.15)
    r.h(2, "6.8  Savings Ledger")
    r.para("Only findings that reached the *verified* state contribute to savings. In the demonstration two resources were "
           "fixed and then confirmed by the before/after bill comparison (Table 6.3). The estimate for the two items was "
           "$35.71 a month and the realised saving $33.44 a month, an accuracy of 93.6 %, which the interface rounds to 94 %. "
           "The \"saved to date\" figure of $11.80 is the realised monthly saving multiplied by the days since each "
           "verification divided by 30.4.")
    r.table("Table 6.3: Verified savings in the demo workspace",
            ["Resource", "Cloud", "Estimated (USD / month)", "Realised (USD / month)", "Accuracy"],
            [["Disk web-01_OsDisk_old", "Azure", "19.71", "18.24", "92.5 %"],
             ["EBS volume db-backup-old", "AWS", "16.00", "15.20", "95.0 %"],
             ["**Total**", "", "**35.71**", "**33.44**", "**93.6 %**"]],
            widths=[4.6, 1.6, 3.0, 3.0, 2.8], size=10)

    r.h(2, "6.9  Test Results")
    r.table("Table 6.4: Automated test run (pytest)",
            ["Suite", "Tests", "Result"],
            [["Algorithms (priority, anomaly, forecast, VM verdict, verification)", "23", "passed"],
             ["Full cost-to-action loop on a fake Azure cloud", "1", "passed"],
             ["Static front end and Azure diagnostics", "3", "passed"],
             ["**Total**", "**27**", "**27 passed**"]],
            widths=[10.0, 2.0, 3.0], size=10.5)
    r.para("The integration test exercises the complete loop including permissions and a regression: after a fix is verified the "
           "resource is made to reappear and the test asserts that the finding reopens and the saving is withdrawn.")

    r.h(2, "6.10  Validation on a Real Azure Subscription")
    r.para("The Azure scripts of Section 5.12 are the procedure used to validate the system on a subscription. The expected "
           "and observable results are listed in Table 6.5. The figures in Sections 6.2 to 6.8 are from the demonstration "
           "workspace; results from a customer's own subscription depend on the resources it contains and on Azure's "
           "publication delay of 8 to 24 hours for billing data.")
    r.table("Table 6.5: Validation checklist for a live subscription",
            ["Check", "Expected observation", "When"],
            [["`python -m app.manage check-azure`", "\"Connected: <subscription name>\"", "immediately"],
             ["Workspace created from the settings", "A customer workspace appears next to the demo; the sidebar shows the subscription", "at start-up"],
             ["Planted waste (02-leaks.sh)", "Four findings with the signed-in account as creator, no tags", "minutes (Activity Log delay)"],
             ["Cost charts and budget", "Daily spend by service for the workload", "8 to 24 hours"],
             ["Anomaly (05-spike.sh up)", "A flagged day after about a week of normal days", "about 1 week"],
             ["Fix a finding (delete the leftover disk)", "State changes to resolved, then verified after 3 or more billed days", "about 4 to 8 days"]],
            widths=[5.4, 6.8, 2.8], size=9.5)
    r.h(2, "6.11  Discussion")
    r.para("The results show that the central claim of the project is realised in software: a cost problem is detected, priced, "
           "ranked, owned, acted on and checked against the bill, and the numbers on every page agree with each other. "
           "Three design choices proved important. First, **fingerprints** keep one finding per problem across syncs, so the "
           "history, comments and verification stay attached. Second, **verification against the bill** replaces self-reported "
           "savings; in the demonstration it also reveals that estimates are slightly optimistic (94 % accurate), "
           "information that a plain report would never produce. Third, **read-only access with a managed-identity option** "
           "makes the tool safe to connect, which is a precondition for any real adoption.")
    r.para("Limitations were also observed. Cost data lags by up to a day, so verification of a fix cannot be instantaneous. "
           "Memory pressure on virtual machines is invisible without an agent, so rightsizing advice carries lower confidence. "
           "Owners are known only for resources created in the last 89 days unless tags exist. The scheduler and the login "
           "rate limiter keep state in one process, so the current version targets a single instance. These points are "
           "taken up as future work in the next chapter.")


def chapter7(r):
    r.h(1, "7. CONCLUSION")
    r.para("This project designed, implemented and tested **CloudPulse**, a cloud cost monitoring and optimisation platform that "
           "treats a cost problem as a task to be owned and proven fixed, not as a number on a chart. The system connects to an "
           "Azure subscription with a read-only service principal, a CLI login or a managed identity, reads the bill, inventory, "
           "metrics, recommendations and audit log through a small custom REST client, and converts them into de-duplicated "
           "findings. Transparent algorithms, a robust weekday-aware anomaly detector, Holt's smoothing forecast with an "
           "80 % range and a logarithmic priority score, make every figure explainable. Findings are assigned to the creator "
           "found in the Activity Log, move through a role-controlled lifecycle, and are counted as savings only after seven "
           "days of before-and-after billing confirm the drop. A fixed resource that returns reopens its finding and "
           "withdraws the saving.")
    r.para("The objectives of Chapter 2 were met: Azure data collection with least privilege, detection of idle and wasted "
           "resources, anomaly and budget forecasting, ownership attribution, lifecycle management with an audit trail, "
           "verified savings, secure credential handling and a reproducible Azure test environment. The 27 automated tests "
           "passed, and a headless-browser review of all pages found and fixed a presentation defect. In the demonstration "
           "workspace the system reported $262.94 a month of open waste and $33.44 a month of verified savings at 94 % "
           "estimate accuracy.")
    r.h(2, "7.1  Limitations")
    r.bullets([
        "Savings can only be confirmed after Azure publishes the bill, so verification takes about a week.",
        "Right-sizing uses CPU and network only; memory is not measured.",
        "Creators older than the 90-day Activity Log retention are known only through tags.",
        "The scheduler, login throttle and SQLite database make this version a single-instance application.",
        "AWS and FOCUS support are present but less deep than the Azure integration.",
    ])
    r.h(2, "7.2  Future Enhancements")
    r.bullets([
        "Sign-in with Microsoft Entra ID (OpenID Connect) so that organisations can use their existing accounts.",
        "E-mail, Microsoft Teams and Slack notifications in addition to the in-app inbox.",
        "Google Cloud collector and deeper AWS coverage (idle load balancers, unused NAT gateways, snapshots).",
        "Reservation and savings-plan coverage analysis and purchase recommendations.",
        "Tag-compliance policies with owner reminders, and showback or chargeback reports by team.",
        "Optional, approval-gated remediation, for example deallocating a stopped VM after the owner confirms.",
        "PostgreSQL as the default store with a shared job queue for multi-instance deployment.",
        "Memory and disk metrics through the Azure Monitor agent for more accurate right-sizing.",
    ])


REFERENCES = [
    "Microsoft, \"Azure Cost Management and Billing documentation,\" Microsoft Learn. [Online]. Available: https://learn.microsoft.com/azure/cost-management-billing/",
    "FinOps Foundation, \"What is FinOps?\" [Online]. Available: https://www.finops.org/introduction/what-is-finops/",
    "S. Ramírez, \"FastAPI framework documentation.\" [Online]. Available: https://fastapi.tiangolo.com/",
    "SQLAlchemy Project, \"SQLAlchemy 2.0 documentation.\" [Online]. Available: https://docs.sqlalchemy.org/",
    "C. Percival and S. Josefsson, \"The scrypt password-based key derivation function,\" RFC 7914, IETF, Aug. 2016.",
    "Python Cryptographic Authority, \"Fernet (symmetric encryption),\" cryptography documentation. [Online]. Available: https://cryptography.io/en/latest/fernet/",
    "FinOps Foundation, \"FOCUS: FinOps Open Cost and Usage Specification.\" [Online]. Available: https://focus.finops.org/",
    "B. Iglewicz and D. C. Hoaglin, How to Detect and Handle Outliers, vol. 16 of The ASQC Basic References in Quality Control. Milwaukee, WI, USA: ASQC Quality Press, 1993.",
    "C. C. Holt, \"Forecasting seasonals and trends by exponentially weighted moving averages,\" Int. J. Forecasting, vol. 20, no. 1, pp. 5-10, 2004 (reprint of the 1957 ONR memorandum).",
    "R. J. Hyndman and G. Athanasopoulos, Forecasting: Principles and Practice, 3rd ed. Melbourne, Australia: OTexts, 2021. [Online]. Available: https://otexts.com/fpp3/",
    "D. Hardt, Ed., \"The OAuth 2.0 authorization framework,\" RFC 6749, IETF, Oct. 2012.",
    "Microsoft, \"Azure Resource Manager REST API reference,\" Microsoft Learn. [Online]. Available: https://learn.microsoft.com/rest/api/azure/",
    "Microsoft, \"Overview of Azure Resource Graph,\" Microsoft Learn. [Online]. Available: https://learn.microsoft.com/azure/governance/resource-graph/overview",
    "Microsoft, \"Azure Monitor metrics overview,\" Microsoft Learn. [Online]. Available: https://learn.microsoft.com/azure/azure-monitor/essentials/data-platform-metrics",
    "Microsoft, \"Azure activity log,\" Microsoft Learn. [Online]. Available: https://learn.microsoft.com/azure/azure-monitor/essentials/activity-log",
    "Microsoft, \"Azure Advisor documentation,\" Microsoft Learn. [Online]. Available: https://learn.microsoft.com/azure/advisor/",
    "Microsoft, \"Azure Retail Prices REST API,\" Microsoft Learn. [Online]. Available: https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices",
    "Microsoft, \"Azure built-in roles,\" Microsoft Learn. [Online]. Available: https://learn.microsoft.com/azure/role-based-access-control/built-in-roles",
    "Microsoft, \"What are managed identities for Azure resources?\" Microsoft Learn. [Online]. Available: https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview",
    "J. R. Storment and M. Fuller, Cloud FinOps, 2nd ed. Sebastopol, CA, USA: O'Reilly Media, 2023.",
]


def chapter8(r):
    r.h(1, "8. REFERENCE")
    for i, ref in enumerate(REFERENCES, 1):
        p = r.para(f"[{i}]  {ref}", align="l", size=12, spacing=1.3, after=5)
        p.paragraph_format.left_indent = r.cm(1.1) if hasattr(r, "cm") else None
        p.paragraph_format.first_line_indent = r.cm(-1.1) if hasattr(r, "cm") else None
