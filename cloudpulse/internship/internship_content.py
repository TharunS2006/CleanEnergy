"""Chapters 1-5, references and appendices of the internship report.
Yellow [CHECK ...] items are things only the student can fill in or confirm."""
A = "assets/"
ORG = "Trios Technologies Private Limited"


def chapters(r):
    ch1(r); r.page_break()
    ch2(r); r.page_break()
    ch3(r); r.page_break()
    ch4(r); r.page_break()
    ch5(r); r.page_break()
    refs(r); r.page_break()
    appendices(r)


# =============================================================== CHAPTER 1
def ch1(r):
    r.h(1, "CHAPTER 1 - INTRODUCTION")
    r.h(2, "1.1 Internship Overview")
    r.para(f"The internship was undertaken at {ORG}, located at Rani Arcade, #24/5, 1st Avenue, Ashok Nagar, Chennai - 83 "
           "(near Ashok Pillar). It ran for 15 days, from 08 June 2026 to 22 June 2026, as part of the Bachelor of Engineering "
           "programme in Computer Science and Engineering at R.M.K. College of Engineering and Technology.")
    r.para("The internship was in the domain of **cloud computing**. The completion letter issued by the company records that "
           "the student gained practical exposure to cloud computing concepts during this period. The learning was applied to a mini "
           "project, **CloudPulse**, a cloud cost monitoring and optimisation platform for Microsoft Azure. Its development was "
           "started during the internship and extended afterwards. CloudPulse detects wasted cloud spend, assigns each problem to "
           "the person who created the resource, tracks the fix and proves the saving on the next bill.")
    r.para("The technologies and tools used included Python, FastAPI, SQLAlchemy, JavaScript, the Azure CLI and Azure Resource "
           "Manager (ARM) APIs, Docker, Git and GitHub.")
    r.h(2, "1.2 Objectives of Internship")
    r.bullets([
        "Gain practical exposure to cloud computing concepts: service and deployment models, virtualisation, storage, networking, "
        "identity and access management, governance, monitoring and cloud pricing.",
        "Understand how real cloud resources are billed and how avoidable spend arises from idle and forgotten resources.",
        "Learn how to access a cloud account securely with a least-privilege, read-only identity.",
        "Apply the concepts in a working mini project using Python, REST APIs and the Azure CLI.",
        "Understand planning, development, testing and documentation of a software project.",
        "Use version control and maintain organised project code."])
    r.h(2, "1.3 Organization Profile")
    r.h(3, "Company Overview")
    r.para(f"{ORG} (Trios Technologies Pvt. Ltd.) is located in Ashok Nagar, Chennai. Its letterhead carries the tagline "
           "“We There Wherever The Technology Is” and lists the website www.triostechnology.com, the e-mail address "
           "support@triostechnology.com and the telephone number 044 4854 0077. The company offered the cloud computing internship "
           "described in this report. [[CHECK: add 2 to 3 lines about the company's business and services from its website or from "
           "your mentor]]")
    r.table("Organization Details", ["Item", "Details"],
            [["Organization", ORG],
             ["Address", "Rani Arcade, #24/5, 1st Avenue, Ashok Nagar, Chennai - 83 (Near Ashok Pillar)"],
             ["Website", "www.triostechnology.com"],
             ["E-mail / Phone", "support@triostechnology.com / 044 4854 0077"],
             ["Internship domain", "Cloud Computing"],
             ["Internship duration", "08 June 2026 to 22 June 2026 (15 days)"],
             ["Industry mentor", "Ms. Kalaiyarasi S"]], [4.2, 11.7], 10.5, center=False)
    r.placeholder_box("[[Paste a photograph of Trios Technologies (building or your workspace) here]]",
                      f"{ORG}, Ashok Nagar, Chennai", 3.2)
    r.h(3, "Vision and Mission")
    r.para("[[CHECK: add the company's vision and mission from its website, or delete this heading if it is not available]]")
    r.h(3, "Products and Services")
    r.bullets(["Internship domain offered: cloud computing",
               "[[CHECK: add the company's other products and services from its website]]"])
    r.h(2, "1.4 Scope of Internship")
    r.h(3, "Department Assigned")
    r.para("The internship focused on the cloud computing domain.")
    r.h(3, "Nature of Work")
    r.bullets([
        "Studying cloud computing concepts and the Microsoft Azure services behind them.",
        "Analysing why cloud spend is wasted and defining the CloudPulse mini project.",
        "Designing a read-only Azure integration using a service principal, role-based access control and OAuth 2.0 tokens.",
        "Developing detection rules and analytics in Python, a web API with FastAPI and a browser interface.",
        "Testing the project with automated tests and a scripted Azure environment.",
        "Using Git and GitHub to manage the project code."])
    r.h(3, "Expected Outcomes")
    r.para("The expected outcomes included practical knowledge of cloud computing concepts and Azure services, an understanding "
           "of cloud cost and security practice, improved Python and API development skills, stronger testing and documentation "
           "habits, and a better understanding of how a cloud-based software project is planned and delivered.")


# =============================================================== CHAPTER 2
def ch2(r):
    r.h(1, "CHAPTER 2 - INTERNSHIP ACTIVITIES")
    r.h(2, "2.1 Roles and Responsibilities")
    r.bullets([
        "Understand the objectives of the cloud computing internship and the problem to be solved.",
        "Study cloud computing concepts and Azure services relevant to cost, identity and monitoring.",
        "Design and implement the CloudPulse mini project: cloud access, detection, scoring and verification.",
        "Create the user interface for findings, costs, anomalies and budgets.",
        "Test the application and document the work.",
        "Manage project code with Git and GitHub."])
    r.h(2, "2.2 Weekly Activity Log")
    r.table("Weekly Activity Log", ["Period", "Activities Performed", "Skills Acquired", "Evidence"],
            [["Week 1\n(08 - 14 June 2026)",
              "Orientation to the organization and the cloud computing domain; studied cloud service and deployment models, "
              "virtualisation and compute, storage, networking and identity and access management; identified avoidable cloud "
              "spend as the problem to solve.",
              "Cloud fundamentals, Azure services, IAM and RBAC", "Study notes"],
             ["Week 2\n(15 - 22 June 2026)",
              "Studied resource governance, monitoring, cloud pricing and FinOps; planned the architecture and began the first "
              "version of CloudPulse with read-only Azure access and waste detection rules.",
              "Python, REST APIs, Azure Monitor and Cost Management, design", "CloudPulse source code"],
             ["Final Review",
              "Reviewed the completed work, organised notes and project files, and received the internship completion letter.",
              "Documentation, professional development", "Internship completion letter"]],
            [2.8, 6.8, 3.5, 2.8], 10)
    r.para("[[CHECK: edit this log so that every row matches what you actually did and learned during the internship]]", "l", 10.5)
    r.h(2, "2.3 Tools and Technologies Used")
    r.table("Tools and Technologies Used", ["Tool / Technology", "Purpose", "Practical Application"],
            [["Azure Portal and Cloud Shell", "Manage and inspect Azure", "Created and checked test resources"],
             ["Azure CLI", "Command-line cloud access", "Scripts that create the workload, planted waste and read-only identity"],
             ["Microsoft Entra ID and RBAC", "Identity and permissions", "Service principal with Reader and Cost Management Reader roles"],
             ["Azure Resource Manager REST APIs", "Read cloud data", "Cost Management, Resource Graph, Monitor, Activity Log and Advisor calls"],
             ["Python 3", "Back-end logic", "Detection rules, anomaly, forecast and priority algorithms"],
             ["FastAPI and Uvicorn", "Web API and server", "Authentication, findings, savings and budget endpoints"],
             ["SQLAlchemy and SQLite", "Data storage", "Findings, costs, owners, audit log and users"],
             ["HTML, CSS and JavaScript", "User interface", "Single-page application with SVG charts"],
             ["Docker", "Packaging", "Container image and Docker Compose set-up"],
             ["Git and GitHub", "Version control", "Managed project code and changes"],
             ["pytest", "Testing", "27 automated tests"]],
            [4.6, 4.2, 7.1], 10)
    r.h(2, "2.4 Projects and Tasks Completed")
    r.h(3, "Project 1: CloudPulse - Cloud Cost Monitoring and Optimisation Platform")
    r.para("**Objective:** To build a transparent, read-only platform that finds wasted spend in a real Azure subscription, "
           "assigns each problem to its creator, tracks the fix and proves the saving on the bill.")
    r.para("**Description:** CloudPulse carries every cost problem through the loop *Signal, Context, Finding, Ownership, Action, "
           "Verification*. It reads the bill, the resource inventory, virtual machine metrics, Azure Advisor recommendations and the "
           "Activity Log; detects idle disks, unused public IP addresses, orphaned snapshots and stopped-but-billed virtual machines; "
           "finds spend anomalies; forecasts month-end spend and budget breaches; scores every finding from P1 to P4; and counts a "
           "saving only after seven days of billed cost confirm it.")
    r.para("**Outcome:** A working application of about 8,500 lines with a Python back end, a browser interface, Azure setup scripts "
           "and 27 automated tests. In its demonstration workspace it reported $262.94 a month of open waste and $33.44 a month "
           "of verified savings. The project is described in detail in Chapter 4.")
    r.h(3, "Task 2: Cloud Computing Concept Study")
    r.para("The cloud computing concepts were studied as twelve topics: service and deployment models, virtualisation and compute, "
           "storage, networking, identity and access management, resource management and governance, monitoring, cloud economics, "
           "FinOps, elasticity, security and shared responsibility, and automation and containers. Each topic was connected to a "
           "feature of CloudPulse, as summarised in Chapter 3.")
    r.h(2, "2.5 Challenges Faced and Solutions")
    r.table("Challenges Faced and Solutions", ["Challenge", "Solution", "Learning"],
            [["Azure publishes cost data 8 to 24 hours late", "Verification waits for 3 billed days after a fix; the demo uses a fixed clock",
              "Billing is delayed and must be planned for"],
             ["Finding who created a resource when tags are missing", "Read the earliest successful write in the Activity Log; treat GUID callers as service identities",
              "Audit logs are a reliable source of ownership"],
             ["Connecting safely to a real subscription", "Read-only service principal, least-privilege roles, Fernet-encrypted secret, managed identity option",
              "Least privilege and secret handling"],
             ["Student subscriptions allow only some regions", "Scripts read the allowed-location policy and pick a permitted region", "Governance policies affect deployment"],
             ["Dashboard showed sample data instead of Azure when credentials were missing", "Added a start-up message, a `check-azure` command and an admin banner",
              "Failures must explain themselves"],
             ["Main text was almost invisible because of a mistyped colour value", "Found by a headless-browser review; fixed and covered by a regression test",
              "Visual checks catch what unit tests cannot"]],
            [4.9, 6.2, 4.8], 10)


# =============================================================== CHAPTER 3
def ch3(r):
    r.h(1, "CHAPTER 3 - LEARNING OUTCOMES")
    r.h(2, "3.1 Technical Skills")
    r.para("The internship developed my practical knowledge of cloud computing concepts and Azure services, Python and API "
           "development, secure cloud access, testing and version control.")
    r.bullets(["Cloud service models, virtualisation, storage, networking and cloud pricing",
               "Identity and access management: service principals, RBAC, OAuth 2.0 tokens and managed identities",
               "Azure Resource Manager APIs: Cost Management, Resource Graph, Monitor, Activity Log and Advisor",
               "Python, FastAPI and SQLAlchemy",
               "Statistics used in practice: robust z-score anomaly detection and exponential smoothing forecasts",
               "Docker, the Azure CLI and shell scripting",
               "Git and GitHub, automated testing with pytest"])
    r.table("Cloud Computing Concepts Learned and Where They Were Applied",
            ["Concept", "What was learned", "Applied in CloudPulse"],
            [["Service and deployment models", "IaaS, PaaS, SaaS; public, private, hybrid", "IaaS resources monitored; PaaS and SaaS delivery"],
             ["Virtualisation and compute", "VM sizes; stopped versus deallocated power states", "Stopped-but-billed VM and idle / oversized VM rules"],
             ["Cloud storage", "Managed disk tiers, snapshots, billing by size", "Unattached disk and orphaned snapshot rules"],
             ["Cloud networking", "Public IPs, static and dynamic allocation", "Idle static public IP rule"],
             ["Identity and access management", "Entra ID, service principals, RBAC, least privilege", "Read-only identity and token flow"],
             ["Governance", "ARM, resource groups, tags, policy", "Resource Graph inventory, owner tags, region policy"],
             ["Monitoring", "Azure Monitor metrics, Activity Log, Advisor", "VM verdict, creator lookup, Advisor evidence"],
             ["Cloud economics", "Pay-as-you-go, reservations, billing delay", "Price book and verification wait"],
             ["FinOps", "Inform, optimise and operate", "The cost-to-action loop"],
             ["Elasticity", "Rapid scaling changes cost quickly", "Cost spike test for anomaly detection"],
             ["Security", "Shared responsibility, encryption, hashing", "Fernet, scrypt, read-only collector"],
             ["Automation and DevOps", "CLI, containers, CI", "Azure scripts, Docker, GitHub Actions"]],
            [3.8, 5.8, 6.3], 9.5, center=False)
    r.h(2, "3.2 Professional Skills")
    r.bullets([
        "Communication: Improved my ability to understand a problem and explain technical decisions in writing and in diagrams.",
        "Time management: Prioritised study and development tasks within the fixed internship period.",
        "Problem solving: Strengthened my ability to analyse technical problems, such as unknown resource owners, and find solutions.",
        "Critical thinking: Evaluated whether a claimed saving is real by checking it against the bill.",
        "Professional ethics: Practised responsible work by using read-only access and protecting credentials."])
    r.h(2, "3.3 Industry Practices")
    r.bullets([
        "Coding standards: Kept the algorithms as small, documented functions that can be tested without a database or network.",
        "Quality: Wrote 27 automated tests and reviewed every page in a headless browser.",
        "Documentation: Wrote a README, a set-up guide and an architecture description.",
        "Version control: Used Git and GitHub to manage project code and changes.",
        "Security practice: Least-privilege access, encrypted secrets, hashed passwords and rate limiting.",
        "Development process: Followed requirement understanding, design, development, testing, debugging and improvement."])
    r.h(2, "3.4 OBE Attainment")
    r.table("Program Outcome (PO) Mapping", ["Activity", "Program Outcome", "Evidence / Justification"],
            [["Requirement understanding", "PO1 - Engineering Knowledge", "Applied computer science and cloud computing fundamentals to understand the problem."],
             ["Problem identification", "PO2 - Problem Analysis", "Analysed why cloud spend is wasted and what data is needed to prove a saving."],
             ["Design and development", "PO3 - Design/Development of Solutions", "Designed and implemented the CloudPulse architecture, algorithms and interface."],
             ["Testing and validation", "PO4 - Investigation of Complex Problems", "Validated the algorithms with hand-computed tests and an Azure test environment."],
             ["Development tools", "PO5 - Modern Tool Usage", "Used the Azure CLI, ARM APIs, FastAPI, Docker, Git and GitHub."],
             ["Cost and security awareness", "PO6 - Engineer and Society", "Protected customer credentials and helped avoid wasteful spending."],
             ["Efficient resource use", "PO7 - Environment and Sustainability", "Detected idle cloud resources that consume infrastructure without delivering value."],
             ["Professional conduct", "PO8 - Ethics", "Used read-only access and responsible handling of secrets."],
             ["Mentor interaction", "PO9 - Individual and Team Work", "Worked under mentor guidance during the internship."],
             ["Report preparation", "PO10 - Communication", "Documented the work in this report and in the project README."],
             ["Project completion", "PO11 - Project Management and Finance", "Planned tasks, and applied cost-management practice to cloud finance."]],
            [3.9, 4.8, 7.2], 9.5)
    r.table("Program Specific Outcome (PSO) Mapping", ["Internship Activity", "PSO", "Evidence"],
            [["Cloud-based application development", "PSO1", "Project source code, screenshots and report"],
             ["Use of modern cloud technologies", "PSO2", "Azure CLI, ARM APIs, Docker, Git and GitHub"],
             ["Testing, security and professional development", "PSO3", "27 automated tests, internship letter"]],
            [6.0, 2.5, 7.4], 10)
    r.table("Graduate Attribute / Professional Competency Mapping",
            ["Internship Activity", "Graduate Attribute / Professional Competency", "Evidence"],
            [["Industrial training", "Technical Competency", "Internship completion letter"],
             ["Software development", "Problem Solving Skills", "Project source code"],
             ["Mentor guidance", "Teamwork and Leadership", "Industry mentor"],
             ["Project documentation", "Communication Skills", "Internship report"],
             ["Workplace activities", "Professional Ethics", "Internship participation"],
             ["Learning new technologies", "Lifelong Learning", "Practical project implementation"]],
            [4.6, 6.0, 5.3], 10)
    r.table("Sustainable Development Goal (SDG) Mapping", ["Activity", "SDG", "Contribution"],
            [["Development of digital applications", "SDG 9 - Industry, Innovation and Infrastructure", "Promoted innovation through cloud-based software."],
             ["Detecting idle cloud resources", "SDG 12 - Responsible Consumption and Production", "Encouraged efficient use of cloud resources."],
             ["Professional development", "SDG 8 - Decent Work and Economic Growth", "Developed industry-relevant technical and professional skills."]],
            [4.6, 5.6, 5.7], 10)


# =============================================================== CHAPTER 4
def ch4(r):
    r.h(1, "CHAPTER 4 - CASE STUDY / MINI PROJECT")
    r.para("CloudPulse - Cloud Cost Monitoring and Optimisation Platform was selected as the main case study because its "
           "development combined the cloud computing concepts studied during the internship with a working, tested application.")
    r.h(2, "4.1 Problem Statement")
    r.para("Cloud resources are easy to create and easy to forget. A virtual machine shut down from inside the operating system "
           "still bills for compute, a detached disk keeps charging for every gigabyte, and an unused static public IP address and an "
           "orphaned snapshot add cost every day. Native cost consoles show how much was spent but do not say who owns the "
           "waste, what to fix first, whether the fix worked or whether the waste came back. CloudPulse addresses these questions "
           "by carrying each cost problem from detection to a saving verified on the bill.")
    r.h(2, "4.2 Methodology")
    r.para("The project followed the loop **Signal, Context, Finding, Ownership, Action, Verification**. On every synchronisation "
           "CloudPulse (1) signs in to Azure, (2) reads the bill from Cost Management, (3) lists the inventory through Resource "
           "Graph, (4) reads 14 days of virtual machine metrics from Azure Monitor and Advisor recommendations, (5) finds the creator "
           "of each resource in the Activity Log, (6) applies the detection rules, (7) scores and de-duplicates findings, "
           "(8) runs the workspace detectors for anomalies, budget risk and untagged spend, and (9) verifies fixed findings.")
    r.table("Azure Services and Interfaces Used", ["Service", "Interface", "Purpose", "Permission"],
            [["Microsoft Entra ID", "OAuth 2.0 token endpoint", "Issue a Bearer token", "App registration"],
             ["Cost Management", "Microsoft.CostManagement/query", "Daily cost by service and resource", "Cost Management Reader"],
             ["Resource Graph", "Microsoft.ResourceGraph/resources", "Disks, IPs, snapshots, VMs, tags", "Reader"],
             ["Azure Monitor", "Microsoft.Insights/metrics", "VM CPU and network metrics", "Reader"],
             ["Activity Log", "Microsoft.Insights/eventtypes", "Who created each resource", "Reader"],
             ["Azure Advisor", "Microsoft.Advisor/recommendations", "Cost recommendations", "Reader"],
             ["Retail Prices API", "prices.azure.com", "List-price fallback", "None (public)"]],
            [3.2, 4.8, 4.4, 3.5], 9.5)
    r.h(2, "4.3 Implementation")
    r.h(3, "System Architecture")
    r.para("CloudPulse is a three-tier web application. The client tier is a single-page application. The server tier is one "
           "Python process (FastAPI) containing the API and security layer, the scheduler, the collectors and the analytics. The "
           "data tier is a SQL database with the server's configuration. Azure is an external system that is only read. Figure 3, "
           "on the next page, shows the components and the numbered flows, including the Azure credential path.")
    r.landscape()
    r.figure(A + "fig_architecture.png", "CloudPulse system architecture with the Azure credential and data flows", width_cm=24.4)
    r.portrait()
    r.h(3, "Azure Credentials")
    r.para("Everything CloudPulse knows about a subscription comes through one identity. An **app registration** with a "
           "**service principal** is created in the Microsoft Entra ID tenant; it has a **client ID** and a **client secret**. "
           "The service principal is granted the **Reader** and **Cost Management Reader** roles on the subscription only, so it "
           "cannot create, change or delete anything. CloudPulse exchanges the tenant ID, client ID and secret for a short-lived "
           "OAuth 2.0 **access token** (valid about an hour) and sends it as a Bearer token with every read request; Azure "
           "Resource Manager validates the token and the role assignment before answering. When the application runs on Azure App "
           "Service, a **managed identity** is used instead and no secret exists at all.")
    r.figure(A + "fig_credflow.png", "Azure credential creation, token acquisition and read-only request sequence", width_cm=10.6)
    r.para("A secret entered in the interface is encrypted with Fernet (AES-128 and an HMAC integrity check) using a key derived "
           "from the server's `APP_SECRET_KEY`, and is never returned by the API. If sign-in fails, the command "
           "`python -m app.manage check-azure` reports exactly why.")
    r.h(3, "Detection Rules")
    r.table("Waste Detection Rules", ["Finding", "Rule", "Monthly impact", "Confidence"],
            [["Unattached disk", "diskState = Unattached", "Size × list price of the disk tier", "0.95"],
             ["Idle public IP", "Static, no IP configuration, no NAT gateway", "Standard public IP price", "0.95"],
             ["Orphaned snapshot", "Source disk deleted, or older than 30 days", "Size × snapshot price", "0.90 / 0.60"],
             ["VM stopped but billed", "Power state stopped (not deallocated)", "Compute hours × VM price + disks", "0.90"],
             ["Idle VM", "p95 CPU < 5% and network < 5 MB per hour", "Compute price of the size", "0.85"],
             ["Oversized VM", "p95 CPU < 20% and peak < 80%", "Price difference to the next smaller size", "0.70"]],
            [3.4, 5.4, 4.8, 2.3], 9.5)
    r.h(3, "Algorithms")
    r.para("**Anomaly detection** uses a weekday-aware robust z-score: a day is flagged when z = (x − median) / (1.4826 × MAD) "
           "exceeds 3.5 against the same weekday of the previous four weeks, and the excess is at least 20% of the usual cost. "
           "**Forecasting** uses Holt's linear exponential smoothing with weekday factors and an 80% range to predict month-end spend "
           "and the day a budget is breached. The **priority score** is 100 × (0.6 × impact score + 0.4 × severity weight) × "
           "confidence × age factor, where the impact score is logarithmic, giving bands P1 (70 and above), P2 (45), P3 (25) and P4. "
           "**Verification** compares the resource's average daily cost in the 7 days before a fix with the days after it, needs at "
           "least 3 billed days, and records the realised monthly saving; a fixed resource that reappears reopens its finding and "
           "withdraws the saving.")
    r.h(3, "Finding Lifecycle and Security")
    r.para("A finding moves through open, assigned, in progress, resolved and verified, or is dismissed with a reason or snoozed. "
           "Administrators and workspace owners may perform every action, the assignee may start and resolve, and viewers can only "
           "read. Passwords are hashed with scrypt, sessions are server-side with HttpOnly cookies, state-changing requests need a "
           "custom header against cross-site forgery, and failed logins are limited to 8 per 15 minutes.")
    r.h(3, "Azure Test Environment and Testing")
    r.para("Bash scripts with the Azure CLI create a small workload (a VM, a web app, a SQL database and storage), plant four "
           "untagged wasted resources (an unattached disk, an unused public IP, an orphaned snapshot and a VM stopped the wrong way), "
           "create the read-only identity, deploy the application and trigger a cost spike. The project has 27 automated tests: "
           "23 for the algorithms, one full-loop test against a fake Azure cloud covering permissions and the reappearing-resource "
           "regression, and three for the front end and Azure diagnostics.")
    r.h(2, "4.4 Results and Discussion")
    r.para("The screenshots below were taken from the running application in its demonstration workspace, which runs the same "
           "collection, detection, scoring and verification code as a live Azure workspace on a bundled FinOps FOCUS sample bill.")
    r.figure(A + "shot_login.png", "CloudPulse sign-in page", width_cm=15.0)
    r.para("**Sign-in page.** Users sign in with the account created by the administrator, or press *Explore the demo* for a "
           "read-only sample workspace. The right-hand panel states the value of the product with live figures: $123.73 a month "
           "is going to 7 idle resources and CloudPulse traced who created 6 of them, with examples such as the stopped VM "
           "gpu-trial-01 ($70.08), the unattached EBS volume db-backup-old ($16.00) and the stopped EC2 instance load-test-runner ($8.00).")
    r.figure(A + "shot_overview.png", "Overview page (administrator view of the demo workspace)", width_cm=15.0)
    r.para("**Overview.** The page answers what was spent, what needs fixing and what fixing has saved. Spend for the month was "
           "$2,829.99, 109% of the $2,600 budget. Six findings worth $262.94 a month are waiting to be fixed, and verified fixes "
           "have already cut $33.44 a month, with estimates 94% accurate. The loop panel shows the findings by stage: 5 open "
           "($192.86), 1 owned ($70.08), 0 fixed and being checked, and 2 verified ($33.44).")
    r.figure(A + "shot_costs.png", "Cost explorer with the daily tooltip for 18 September 2024", width_cm=15.0)
    r.para("**Cost explorer.** Spend is broken down by service or provider: total $2,829.99, 80 services billed, daily average "
           "$94.33, and Amazon Elastic Compute Cloud the largest service. The tooltip for 18 September 2024 lists each service's cost "
           "that day, adding up to $201.95.")
    r.figure(A + "shot_anomalies.png", "Anomalies page showing the flagged day 24 September 2024", width_cm=15.0)
    r.para("**Anomalies.** One anomaly is tracked, with an excess of $95.71 above the usual cost. On 24 September 2024 the day cost "
           "$169.26 against a usual $73.55 (z-score 7.9); Amazon Elastic Compute Cloud explains 99.1% of the increase. The spike is "
           "still running high, so it is not yet verified as back to normal on the bill.")
    r.figure(A + "shot_budgets.png", "Budgets page with the cumulative spend line and the budget breach marker", width_cm=15.0)
    r.para("**Budgets.** The budget of $2,600 was passed on 28 September 2024 and the month ended at $2,829.99, which is "
           "$229.99 over. The chart shows cumulative spend against the budget line with a marker at the breach day; for a month "
           "in progress it adds the forecast and an 80% range.")
    r.table("Verified Savings in the Demo Workspace", ["Resource", "Estimated (USD/month)", "Realised (USD/month)", "Accuracy"],
            [["Disk web-01_OsDisk_old (Azure)", "19.71", "18.24", "92.5%"],
             ["EBS volume db-backup-old (AWS)", "16.00", "15.20", "95.0%"],
             ["**Total**", "**35.71**", "**33.44**", "**93.6%**"]], [6.4, 3.4, 3.4, 2.7], 10)
    r.para("**Discussion.** The results show the complete loop working: problems are detected, priced, ranked, owned, acted on and "
           "checked against the bill, and the figures agree across all pages. Verification shows that estimates are slightly "
           "optimistic (93.6% accurate), information a plain report would never give. Limitations are the billing delay of up to "
           "a day, no memory metrics for virtual machines, and creators known only for the last 89 days of the Activity Log "
           "unless tags exist.")
    r.h(2, "4.5 Conclusion")
    r.para("CloudPulse was started as a mini project during the internship and applies the cloud computing concepts studied "
           "there to a real problem. Building it improved my understanding of cloud billing, identity and access management, "
           "monitoring and secure design, and of testing and documenting a software project. The project also strengthened my "
           "experience with Python, REST APIs, the Azure CLI and the tools used to build and operate cloud-based applications.")


# =============================================================== CHAPTER 5
def ch5(r):
    r.h(1, "CHAPTER 5 - REFLECTION AND CONCLUSION")
    r.h(2, "5.1 Key Learning")
    r.bullets(["Understanding cloud computing concepts and how cloud resources are billed.",
               "Accessing a cloud account securely with a least-privilege, read-only identity.",
               "Using Azure Resource Manager APIs, the Azure CLI and Python to read and analyse cloud data.",
               "Applying statistics, such as anomaly detection and forecasting, to a real problem.",
               "Designing, testing and documenting a software project.",
               "Managing source code with Git and GitHub.",
               "Communicating technical work professionally."])
    r.h(2, "5.2 Self-Assessment")
    r.h(3, "Strengths")
    r.para("During the internship, I improved my ability to learn new technologies, understand requirements, solve technical "
           "problems, test and document my work, and apply theory to a practical project.")
    r.h(3, "Areas for Improvement")
    r.para("I plan to strengthen my knowledge of Azure and other cloud platforms in more depth, infrastructure as code, "
           "databases, front-end frameworks, continuous deployment and large-scale system design.")
    r.h(3, "Career Readiness")
    r.para("The internship increased my confidence in working with cloud technologies and strengthened my interest in cloud "
           "computing, DevOps and software engineering.")
    r.h(2, "5.3 Future Scope")
    r.bullets(["Sign-in with Microsoft Entra ID and e-mail, Teams and Slack notifications.",
               "A Google Cloud collector and deeper AWS coverage.",
               "Reservation and savings-plan recommendations.",
               "Tag-compliance policies and showback or chargeback reports.",
               "Approval-gated remediation, such as deallocating a stopped VM after the owner confirms.",
               "PostgreSQL as the default store and a shared job queue for multi-instance deployment.",
               "Memory and disk metrics for more accurate right-sizing."])


def refs(r):
    r.h(1, "REFERENCES")
    r.bullets([
        f"{ORG} - internship training in the cloud computing domain.",
        "Microsoft Learn - Azure Cost Management and Billing, Azure Resource Graph, Azure Monitor, Azure activity log, Azure Advisor "
        "and Azure RBAC documentation. https://learn.microsoft.com/azure/",
        "Microsoft Learn - Azure Resource Manager REST API reference. https://learn.microsoft.com/rest/api/azure/",
        "FinOps Foundation - What is FinOps? and the FOCUS specification. https://www.finops.org/",
        "FastAPI documentation. https://fastapi.tiangolo.com/",
        "SQLAlchemy 2.0 documentation. https://docs.sqlalchemy.org/",
        "Python Cryptographic Authority - Fernet (symmetric encryption). https://cryptography.io/en/latest/fernet/",
        "B. Iglewicz and D. C. Hoaglin, How to Detect and Handle Outliers, ASQC Quality Press, 1993.",
        "R. J. Hyndman and G. Athanasopoulos, Forecasting: Principles and Practice, 3rd ed., OTexts, 2021.",
        "CloudPulse source code and development records (Git repository)."], align="l")


def appendices(r):
    r.h(1, "APPENDICES")
    r.h(2, "Appendix A - Internship Certificate")
    r.para(f"The internship completion letter issued by {ORG} is reproduced as Figure 1. It records the student's name, college, "
           "department, the cloud computing domain and the internship dates, 08 June 2026 to 22 June 2026.")
    r.h(2, "Appendix B - Internship and Organization Photograph")
    r.para("The organization photograph is included as Figure 2 in the organization profile. "
           "[[CHECK: paste your photograph in Figure 2]]")
    r.h(2, "Appendix C - Project Screenshots")
    r.para("Figures 5 to 9 provide visual evidence from the CloudPulse sign-in page, Overview, Cost explorer, Anomalies and "
           "Budgets pages. Figure 3 shows the system architecture and Figure 4 the Azure credential sequence.")
