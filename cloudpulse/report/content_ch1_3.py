"""Chapters 1-3: Introduction, Objectives, Tools and Technologies."""


def chapter1(r):
    r.h(1, "1. INTRODUCTION")
    r.h(2, "1.1  Background")
    r.para("Cloud computing has changed how organisations buy technology. Instead of purchasing servers in advance, a team "
           "can create a virtual machine, a database or a storage account in minutes and pay only for the time and capacity "
           "it uses. Platforms such as Microsoft Azure and Amazon Web Services (AWS) bill by the second or by the hour, and "
           "every resource created from a command line, a portal or an automation script starts to accumulate cost from "
           "the moment it exists [1]. This elasticity is the main strength of the cloud, but it is also its main financial risk: "
           "resources are easy to create and easy to forget [20].")
    r.para("Forgotten resources are the most common source of avoidable cloud spend. A virtual machine that was shut down from "
           "inside the operating system is reported as stopped, yet the platform still reserves the hardware for it and keeps "
           "billing for compute. A data disk that was detached when a project ended continues to be charged for every "
           "gigabyte it holds. A static public IP address that no network interface uses, and a snapshot whose source disk was "
           "deleted months ago, each add a small amount every day. None of these items is large on its own, but across "
           "hundreds of resources and many teams they add up to a significant monthly figure that delivers no value.")
    r.para("The discipline that deals with this problem is called **FinOps** (cloud financial operations). The FinOps "
           "Foundation describes it as a cultural practice in which engineering, finance and business teams share "
           "responsibility for cloud spend and make timely, data-driven decisions [2]. A central idea of FinOps is that "
           "visibility alone is not enough: a cost problem is only solved when somebody who owns it acts and the saving "
           "can be shown on the next bill.")
    r.h(2, "1.2  Problem Statement")
    r.para("Native cost consoles, such as Azure Cost Management and AWS Cost Explorer, are very good at answering "
           "\"how much did we spend and on what?\". They are much weaker at answering the questions that decide whether money "
           "is actually saved:")
    r.bullets([
        "**Which resources are wasted?** A list of the most expensive services does not say which individual resources are idle.",
        "**Who created each wasted resource?** Resource tags are often missing, so the engineer who can switch the resource "
        "off is unknown.",
        "**What should be fixed first?** Without a single score that combines money, severity and confidence, every "
        "item looks equally urgent.",
        "**Was it really fixed?** A closed ticket is not evidence. Only a lower bill proves a saving.",
        "**Did the waste come back?** Resources that are recreated after a clean-up silently erase the benefit.",
    ])
    r.para("The problem addressed by this project is therefore to build a system that does not stop at reporting cost, "
           "but carries each cost problem through detection, prioritisation, ownership, action and independent "
           "verification, while remaining safe to connect to a real cloud account.")
    r.h(2, "1.3  Motivation")
    r.para("The motivation for the project came from three observations. First, a student or small team that experiments "
           "on Azure, for example with the free credit of Azure for Students, can exhaust the credit with a handful of "
           "forgotten resources, and has no tool that explains why. Second, the algorithms that good FinOps tools use, "
           "such as robust anomaly detection and forecasting, are rarely explained: the user sees a number but cannot trace "
           "how it was produced. Third, security is often an afterthought; many tools ask for broad write permissions that "
           "an organisation should never hand to a third party. The project aims to show that a transparent, read-only and "
           "verifiable cost platform can be built with a small, understandable code base.")
    r.h(2, "1.4  Existing Systems and Their Limitations")
    r.para("Three families of tools are commonly used. **Native consoles** (Azure Cost Management, Azure Advisor, AWS Cost "
           "Explorer) are accurate and free, but each covers one provider and stops at reporting or a generic "
           "recommendation. **Commercial FinOps platforms** add multi-cloud views, allocation and dashboards, but are "
           "closed products whose scoring methods are not visible, and which generally require a paid subscription and broad "
           "access. **Home-made scripts** can list idle resources, but they produce one-off reports with no workflow, no "
           "history and no verification. Table 1.1 compares the capabilities that matter for the loop described above.")
    r.table("Table 1.1: Capability comparison of existing approaches and CloudPulse",
            ["Capability", "Native consoles", "Commercial FinOps tools", "Ad-hoc scripts", "CloudPulse"],
            [["Spend dashboards and breakdown", "Yes", "Yes", "Rarely", "Yes"],
             ["Idle and oversized resource detection", "Partial (Advisor)", "Yes", "Partial", "Yes"],
             ["Creator of each resource from audit log", "Manual lookup", "Varies", "No", "Yes, automatic"],
             ["Task workflow (assign, start, fix, dismiss)", "No", "Varies", "No", "Yes"],
             ["Single priority score (P1 to P4)", "No", "Varies", "No", "Yes, explainable"],
             ["Saving checked against the next bill", "No", "Rarely", "No", "Yes, 7-day before/after"],
             ["Saving withdrawn if waste returns", "No", "Rarely", "No", "Yes"],
             ["Read-only access to the account", "n/a", "Varies", "Depends", "Yes, by design"],
             ["Transparent, documented algorithms", "Partial", "Usually no", "Yes", "Yes, open code"]],
            widths=[4.6, 2.6, 2.9, 2.0, 2.9], size=9.5)
    r.h(2, "1.5  Proposed System")
    r.para("**CloudPulse** is a cloud cost monitoring and optimisation platform built around one idea: every cost problem "
           "should travel through the same loop, from the first signal to a verified result. The loop has six stages:")
    r.numbered([
        "**Signal.** On every sync CloudPulse reads the bill, the resource inventory, virtual machine metrics, Azure Advisor "
        "recommendations and the Activity Log.",
        "**Context.** Each signal is priced per month, using the actual billed cost of the resource where it exists and "
        "published list prices otherwise.",
        "**Finding.** The signal becomes one de-duplicated, scored task with its evidence attached.",
        "**Ownership.** The creator found in the Activity Log (tags second) is matched to a CloudPulse user and the "
        "finding is assigned.",
        "**Action.** The owner starts work, fixes, dismisses with a reason or snoozes, with notifications and a full history.",
        "**Verification.** CloudPulse confirms the problem has disappeared and compares seven days of billed cost before "
        "and after. Only then is the saving recorded.",
    ])
    r.para("CloudPulse connects to an Azure subscription through a read-only service principal, an Azure CLI login or an "
           "App Service managed identity. It never creates, changes or deletes anything in the cloud account.")
    r.h(2, "1.6  Scope of the Project")
    r.para("The project delivers a working web application with a Python back end and a browser front end, an Azure test "
           "environment that can be created with scripts, and an automated test suite. The following boundaries apply:")
    r.bullets([
        "Azure is the primary supported cloud. AWS (through boto3) and bills in the FinOps **FOCUS** open format are supported "
        "as optional inputs.",
        "CloudPulse is **read-only**. It recommends fixes (for example the exact `az vm deallocate` command) but never "
        "executes them.",
        "Notifications are in-application only. E-mail and chat integrations are listed as future work.",
        "Savings figures are limited to resource findings; anomalies, budget risks and tagging gaps are tracked and "
        "verified but are not counted as savings.",
    ])
    r.h(2, "1.7  Organisation of the Report")
    r.para("Chapter 2 states the objectives and requirements. Chapter 3 lists the tools and technologies. Chapter 4 presents "
           "the system architecture, including how Azure credentials are created, stored and used. Chapter 5 explains the "
           "methodology: data collection, detection rules, the anomaly, forecast, priority and verification algorithms, the "
           "finding lifecycle and the test environment. Chapter 6 shows and explains the results with screenshots of the "
           "running application. Chapter 7 concludes the report and Chapter 8 lists the references.")


def chapter2(r):
    r.h(1, "2. OBJECTIVES")
    r.h(2, "2.1  Aim")
    r.para("To design and implement a transparent, read-only cloud cost monitoring and optimisation platform that detects "
           "wasted spend in a real Azure subscription, assigns each problem to the person who created the resource, tracks "
           "the fix, and counts a saving only after the bill proves it.")
    r.h(2, "2.2  Specific Objectives")
    r.numbered([
        "To collect cost, inventory, usage, recommendation and audit data from an Azure subscription using the Azure Resource "
        "Manager (ARM) REST interface and a least-privilege identity.",
        "To detect idle and wasted resources: unattached disks, unused public IP addresses, orphaned snapshots, stopped-but-billed "
        "virtual machines, running-but-idle machines and oversized machines.",
        "To detect abnormal daily spend with a robust, weekday-aware statistical method and to explain the services that "
        "caused it.",
        "To forecast month-end spend with an uncertainty range and to predict the day a budget will be exceeded.",
        "To attribute every resource to its creator using the Azure Activity Log, falling back to owner tags.",
        "To turn all signals into a single ranked list of findings, with a score from 0 to 100 and a band from P1 to P4 "
        "that can be explained term by term.",
        "To manage each finding through a defined lifecycle with role-based permissions, comments, notifications and an audit trail.",
        "To verify every claimed saving against billed cost and to withdraw the saving if the problem returns.",
        "To protect stored cloud credentials and user passwords with modern cryptography and to keep the application safe "
        "to expose on the internet.",
        "To provide a reproducible Azure test environment, with intentionally planted waste, and an automated test suite.",
    ])
    r.h(2, "2.3  Functional Requirements")
    r.table("Table 2.1: Functional requirements",
            ["ID", "Requirement", "Where implemented"],
            [["FR1", "Sign in with e-mail and password; forced password change for temporary passwords; one-click read-only demo",
              "routers/auth.py, security.py"],
             ["FR2", "Create customer workspaces; connect Azure (service principal, CLI or managed identity) and optionally AWS",
              "routers/admin.py, services/connections.py"],
             ["FR3", "Read daily cost by service and by resource", "azure_collector.py (Cost Management)"],
             ["FR4", "Read inventory and VM power state; read VM CPU/network metrics", "Resource Graph, Azure Monitor"],
             ["FR5", "Detect waste and rank it by priority", "azure_collector.py, analytics.py"],
             ["FR6", "Find the creator of each resource", "owners.py (Activity Log, tags)"],
             ["FR7", "Spend anomalies with drivers; month forecast with range; budget breach date", "analytics.py, workspace_detectors.py"],
             ["FR8", "Finding workflow: assign, start, resolve, dismiss, snooze, reopen, comment", "findings.py"],
             ["FR9", "7-day before/after saving verification and a savings ledger", "findings.verify, analytics.before_after"],
             ["FR10", "Import bills in the FOCUS format; set a monthly budget", "focus_importer.py, api.py"],
             ["FR11", "Notifications, audit log and CSV export of findings", "api.py, audit.py"]],
            widths=[1.2, 9.3, 4.5], size=10)
    r.h(2, "2.4  Non-Functional Requirements")
    r.table("Table 2.2: Non-functional requirements",
            ["Quality", "Requirement"],
            [["Security", "Least-privilege read-only access; secrets encrypted at rest; scrypt password hashes; HttpOnly session cookies; "
              "CSRF header; login rate limit; security headers"],
             ["Reliability", "Retry on HTTP 429 and 5xx with Retry-After; resumable paging; one failed data source must not stop a sync"],
             ["Explainability", "Every score and forecast can be recomputed by hand from the evidence stored with the finding"],
             ["Portability", "Runs on a laptop, in Docker, on Render or on Azure App Service; SQLite by default, PostgreSQL ready"],
             ["Usability", "No front-end framework to install; responsive from 400 px phones to wide desktops; light and dark themes"],
             ["Maintainability", "Algorithms are pure functions with unit tests; services are separated from routers"],
             ["Cost", "Runs on the free tier of a hosting service; the Azure test workload costs about $2.3 per day"]],
            widths=[3.0, 12.0], size=10)
    r.h(2, "2.5  Success Criteria")
    r.bullets([
        "All automated tests pass (27 tests in the final version).",
        "In demo mode the application shows consistent figures across every page: spend, open waste, verified savings and "
        "budget status.",
        "Against a real Azure subscription, planted waste (a disk, an IP, a snapshot and a stopped VM) appears as findings "
        "with the creator identified, without any tags.",
        "A fixed finding becomes verified only after billed data confirms a drop.",
    ])
    r.h(2, "2.6  Constraints and Assumptions")
    r.para("Azure publishes cost data 8 to 24 hours after usage, so cost charts and verification always lag the actual "
           "change. Azure for Students limits the regions that can be used, which the scripts handle by reading the "
           "subscription's allowed-location policy. Memory utilisation of virtual machines is not available without an "
           "in-guest agent, so oversized-machine findings are given lower confidence. The Activity Log keeps 90 days of "
           "events, so the creator of an older resource may be unknown unless a tag exists.")


def chapter3(r):
    r.h(1, "3. TOOLS AND TECHNOLOGIES")
    r.h(2, "3.1  Hardware and Software Requirements")
    r.table("Table 3.1: Development and run-time environment",
            ["Item", "Specification"],
            [["Processor / memory", "Any 64-bit CPU, 2 GB RAM or more (the application itself uses well under 500 MB)"],
             ["Operating system", "Windows 10/11, Linux or macOS for development; Linux container for deployment"],
             ["Language run-time", "Python 3.10 or newer (Python 3.12 in the Docker image)"],
             ["Browser", "Any current Chromium, Firefox or Safari browser"],
             ["Cloud account", "A Microsoft Azure subscription (Azure for Students is sufficient)"],
             ["Command-line tools", "Azure CLI (or Azure Cloud Shell), Git, Docker (optional)"],
             ["Network", "Outbound HTTPS to management.azure.com, login.microsoftonline.com and prices.azure.com"]],
            widths=[4.0, 11.0], size=10.5)
    r.h(2, "3.2  Back-End Technologies")
    r.para("**Python** was chosen because it has mature libraries for statistics, cryptography and cloud access and because its "
           "readable syntax suits an explainable algorithms layer. The web service is built with **FastAPI** [3], an "
           "asynchronous framework that validates request bodies with **Pydantic** and serves the JSON API and the static "
           "front end from one process, run by the **Uvicorn** server. Persistence uses **SQLAlchemy 2.0** [4], an object-relational "
           "mapper that lets the same models run on **SQLite** during development and on **PostgreSQL** in production.")
    r.para("Background work is handled by **APScheduler**, which starts a synchronisation of every workspace a few seconds after "
           "start-up and then at a configurable interval (360 minutes by default). Long operations run in a worker thread so "
           "the server keeps answering requests. Secrets are protected with the **cryptography** package: the Fernet "
           "recipe for stored cloud credentials and the standard library's **scrypt** for passwords [5], [6].")
    r.h(2, "3.3  Cloud Access Libraries")
    r.para("Authentication to Azure uses the **azure-identity** library, but only for the credential classes "
           "(`ClientSecretCredential`, `ManagedIdentityCredential` and `AzureCliCredential`) that obtain OAuth 2.0 access tokens. "
           "All data calls are made by a custom ARM REST client of about 135 lines that uses only the standard library. The "
           "reason is practical: the Azure management SDKs pull in dozens of dependencies, while the five APIs CloudPulse needs "
           "(Cost Management, Resource Graph, Monitor metrics, Activity Log and Advisor [12]-[16]) share the same simple shape, "
           "`https://management.azure.com` with a Bearer token and an `api-version` parameter. The custom client adds the "
           "behaviour a monitoring tool needs: waiting for `Retry-After` on HTTP 429 and 5xx, following `nextLink` and "
           "`$skipToken` paging, and returning exact error messages. **boto3** is used for the optional AWS collector.")
    r.h(2, "3.4  Front-End Technologies")
    r.para("The user interface is a single-page application written in plain **HTML, CSS and JavaScript** with no framework "
           "or build step. This keeps the deployment to a folder of static files, loads instantly and is easy to read. "
           "All charts (stacked daily bars, the cumulative budget line with a forecast band, before/after bars and sparklines) are "
           "drawn as **SVG** by a 290-line module, so no charting library is needed. Typography uses the self-hosted IBM Plex "
           "and Source Serif fonts under the SIL Open Font License. The design system uses CSS variables for light and dark "
           "themes and breakpoints at 560, 900 and 1180 pixels for responsive layout.")
    r.h(2, "3.5  Azure Services and Interfaces Used")
    r.table("Table 3.2: Azure services, interfaces and the permission they need",
            ["Service", "Interface used", "Purpose in CloudPulse", "Permission"],
            [["Microsoft Entra ID", "login.microsoftonline.com/{tenant}/oauth2/v2.0/token", "Issue a Bearer token for the service principal", "App registration + secret"],
             ["Cost Management", "Microsoft.CostManagement/query (ActualCost, daily)", "Daily cost by service and by resource", "Cost Management Reader"],
             ["Resource Graph", "Microsoft.ResourceGraph/resources (KQL)", "Disks, public IPs, snapshots, VMs, tags", "Reader"],
             ["Azure Monitor", "Microsoft.Insights/metrics", "Hourly CPU and network of each VM for 14 days", "Reader"],
             ["Activity Log", "Microsoft.Insights/eventtypes/management", "Who created each resource (90 days)", "Reader"],
             ["Azure Advisor", "Microsoft.Advisor/recommendations (Cost)", "Microsoft's own cost recommendations", "Reader"],
             ["Retail Prices API", "prices.azure.com/api/retail/prices", "List-price fallback; no sign-in needed", "None (public)"]],
            widths=[2.9, 5.2, 4.3, 2.6], size=9.5)
    r.h(2, "3.6  Data Set")
    r.para("For the demonstration mode the project bundles a 100,000-record sample of the FinOps **FOCUS** (FinOps Open Cost and "
           "Usage Specification) format [7]. It is real, anonymised billing data of an organisation using several cloud providers. "
           "CloudPulse aggregates it into 1,166 daily cost rows from 21 March to 30 September 2024. FOCUS is also the import "
           "format for customers who prefer to upload a bill instead of connecting an account.")
    r.h(2, "3.7  DevOps and Testing Tools")
    r.bullets([
        "**Docker and Docker Compose** package the application with a persistent volume for the database.",
        "**Render** (`render.yaml`) and **Azure App Service** (script `04-deploy-app.sh`) are the two supported hosting targets.",
        "**Bash scripts with the Azure CLI** (`scripts/azure/01` to `06`, `99`) create the test workload, plant waste, create the "
        "read-only identity, deploy the app, trigger a cost spike, attach a custom domain and clean up.",
        "**pytest** runs 27 automated tests; **GitHub Actions** runs them on every push.",
        "**Headless Chromium (Playwright)** was used to load every page in desktop and 400-pixel widths and to capture screenshots.",
    ])
    r.table("Table 3.3: Main Python dependencies (requirements.txt)",
            ["Package", "Version", "Role"],
            [["fastapi", "0.115.0", "Web framework and request validation"],
             ["uvicorn[standard]", "0.30.6", "ASGI server"],
             ["sqlalchemy", "2.0.35", "ORM and database access"],
             ["apscheduler", "3.10.4", "Periodic and manual synchronisation jobs"],
             ["pydantic", "2.9.2", "Typed request and response models"],
             ["python-dotenv", "1.0.1", "Reads settings from the .env file"],
             ["python-multipart", "0.0.32", "File upload for FOCUS bills"],
             ["cryptography", ">= 42", "Fernet encryption of stored cloud secrets"],
             ["azure-identity", "1.25.3", "OAuth 2.0 token credentials for Azure"],
             ["boto3", "1.35.0", "Optional AWS collector"],
             ["pytest, httpx", "8.3.3, 0.27.2", "Automated tests and API test client"]],
            widths=[4.0, 3.0, 8.0], size=10.5)
