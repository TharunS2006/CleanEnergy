import json, subprocess, pathlib
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from ibuilder import IReport, _font
HERE = pathlib.Path(__file__).parent
FIG = HERE.parent / "report" / "diagrams"
R = json.load(open(HERE / "results.json"))
TITLE = "CloudPulse: Closing the Loop from Cloud Cost Signal to Verified Saving with Read-Only Azure Access, Transparent Statistics and Owner Attribution"

r = IReport()
r.doc.core_properties.title = TITLE
r.doc.core_properties.author = "Tamil Mani B; Theja J G; Varunesh D; Viswajith R"
r.doc.core_properties.subject = "Cloud cost optimisation, FinOps, anomaly detection, Microsoft Azure"
r.doc.core_properties.keywords = "FinOps; cloud cost optimisation; anomaly detection; Holt forecasting; Azure RBAC; FOCUS"
# a plain page-number footer is already added by IReport; tighten the style for a paper
for st in ("Normal",):
    r.doc.styles[st].paragraph_format.line_spacing = 1.15
    r.doc.styles[st].font.size = Pt(11)

def P(t, **kw):
    kw.setdefault("size", 11); kw.setdefault("spacing", 1.15); kw.setdefault("after", 6)
    return r.para(t, **kw)
def H1(t): r.h(1, t)
def H2(t): r.h(2, t)
def EQ(t, n):
    p = r.para(f"{t}\t({n})", align="c", size=11, italic=True, spacing=1.2, after=6)
    return p

# ----------------------------------------------------------------- title block
r.para(TITLE, align="c", size=17, bold=True, spacing=1.1, after=10)
r.para("Tamil Mani B, Theja J G, Varunesh D, Viswajith R", align="c", size=12, bold=True, after=2, spacing=1.1)
r.para("Department of Computer Science and Engineering, R.M.K. College of Engineering and Technology (An Autonomous Institution), "
       "Puduvoyal, Tamil Nadu 601 206, India", align="c", size=10.5, italic=True, after=2, spacing=1.1)
r.para("Corresponding author e-mail: [add corresponding author e-mail]", align="c", size=10.5, after=12, spacing=1.1)

r.para("**Abstract.** Cloud spending is easy to start and hard to control. Forgotten virtual machines, orphaned disks and snapshots, "
       "idle public addresses and unexplained cost spikes accumulate quietly, and most cost tools stop at a dashboard that reports what "
       "was spent without telling anyone who should act or whether the action helped. This paper presents CloudPulse, an open "
       "cloud cost monitoring and optimisation platform that carries each cost problem through one complete loop: signal, context, "
       "finding, owner, action and verification. CloudPulse reads a Microsoft Azure subscription through a service principal that "
       "holds only the Reader and Cost Management Reader roles, so it can observe but never change the environment. Detection uses "
       "transparent methods whose every decision can be inspected: a weekday-aware robust z-score (median and median absolute deviation) "
       "for spend anomalies, Holt's linear smoothing with weekday factors for month-end and budget forecasts, percentile verdicts for idle "
       "and oversized machines, and rule checks for unattached disks, idle addresses and stale snapshots. Findings are priced, scored from P1 to P4, "
       "attributed to the identity that created the resource using the Azure Activity Log before tags, and counted as savings only after "
       "seven days of billed cost confirm the drop. We describe the design, give the algorithms in full, and evaluate them on the FinOps "
       "Foundation's public FOCUS sample bill, with 27 automated tests, and with a seeded simulation. In the simulation the detector "
       "found 96–100% of injected spikes of twice the usual cost and matched or exceeded a mean-plus-three-sigma rule at every spike size tested, "
       "at the price of more false alarms, and Holt forecasting with weekday factors reduced seven-day-ahead error against a seven-day "
       "moving average (9.99% against 11.51% MAPE). We state the limits of this evaluation plainly: it is a functional and simulated "
       "evaluation, not a field study.", align="j", size=10.5, spacing=1.12, after=6)
r.para("**Keywords:** FinOps; cloud cost optimisation; anomaly detection; robust statistics; Holt forecasting; Microsoft Azure; "
       "least privilege; FOCUS", align="j", size=10.5, spacing=1.12, after=10)

# ----------------------------------------------------------------- I
H1("I. Introduction")
P("Cloud platforms bill by the second or the hour, and every resource created from a portal, a command line or an automation script starts "
  "accumulating cost the moment it exists [1]. The same elasticity that makes the cloud attractive makes waste easy: resources are quick to "
  "create and easy to forget. A virtual machine stopped from inside its operating system is reported as stopped yet still reserves its compute "
  "allocation; a disk survives the machine it served; a snapshot outlives the disk it protected; a public IP address stays billed after the service "
  "behind it is gone. Practitioner literature on cloud financial management treats this as a central problem of the discipline now called FinOps [2].")
P("Existing tools address part of it. Provider consoles show the bill and issue recommendations; open-source policy engines such as Cloud Custodian "
  "[3] act on rules; commercial platforms add reporting. In our experience as students building and running small Azure workloads, three gaps remained. "
  "First, a recommendation names a resource but not the person who created it, so nobody is accountable. Second, tools that report a saving rarely "
  "check afterwards that the bill actually fell. Third, a tool that is allowed to delete resources needs credentials that are dangerous if leaked, "
  "while a read-only tool is safe but usually stops short of explaining its findings.")
P("CloudPulse is our attempt to close these gaps with deliberately simple, inspectable methods. This paper makes four contributions:")
r.bullets(["**A read-only collection design.** CloudPulse authenticates as an Entra ID service principal with Reader and Cost Management Reader only, "
           "gathers cost, inventory, metrics and audit data through a small REST client, and stores secrets encrypted; it has no write path to the customer's cloud.",
           "**Transparent detection.** Each detector is a short, documented rule or statistic, and each finding carries the evidence that triggered it.",
           "**Ownership and a finding lifecycle.** Findings are attributed to the creating identity from the Azure Activity Log, with tags second, and move through a defined lifecycle.",
           "**Verified savings.** A saving is counted only after a seven-day before-and-after comparison of the billed cost, and a fixed resource that returns reopens its finding."])
P("The remainder of the paper reviews related work (Section II), describes the architecture (III) and the algorithms (IV), reports the implementation (V) and "
  "evaluation (VI), and concludes with limitations and future work (VII).")

# ----------------------------------------------------------------- II
H1("II. Background and Related Work")
P("**Cloud cost management.** Armbrust et al. identified pay-per-use pricing and elasticity as defining properties of cloud computing [1]. The FinOps "
  "community has since formalised practices for allocating, optimising and governing cloud spend [2], and published the FOCUS specification, a vendor-neutral "
  "schema in which Amazon Web Services, Microsoft Azure, Google Cloud and Oracle can export billing data [4]. CloudPulse imports FOCUS files, which lets "
  "its cost analytics run on any provider's bill, while its resource-level checks currently target Azure.")
P("**Anomaly detection in cost series.** The classical rule of flagging values more than three standard deviations from the mean is fragile, because the outliers it "
  "should find inflate the mean and the standard deviation it relies on. Leys et al. recommend the median and the median absolute deviation (MAD) instead [5], and "
  "Rousseeuw and Croux discuss scaling the MAD by 1.4826 to estimate the standard deviation of normal data [6]. Iglewicz and Hoaglin propose a modified "
  "z-score with a conventional cut-off of 3.5 [7]. CloudPulse uses this robust score, but computes it against the same weekday of earlier weeks, because cloud "
  "spend has a strong weekly pattern.")
P("**Forecasting.** Holt's linear exponential smoothing tracks a level and a trend [8], and is covered with its seasonal variants in standard texts [9]. "
  "It needs little data and no training pipeline, which suits a workspace that has only a few weeks of history.")
P("**Security of delegated access.** Least privilege, the principle that an identity should hold only the permissions its task needs, is a long-standing design "
  "rule [10]. Azure applies it through role-based access control, where a security principal, a role and a scope together form an assignment [11], and a "
  "service principal obtains tokens through the OAuth 2.0 client-credentials grant [12]. CloudPulse stores cloud secrets with Fernet authenticated "
  "encryption [13] and user passwords with the scrypt memory-hard function [14].")

# ----------------------------------------------------------------- III
H1("III. System Architecture")
P("Figure 1 shows the three tiers. Browser users (administrator, customer owner, customer viewer and an anonymous demo visitor) reach a web interface "
  "served by a FastAPI application. The application holds the API and security layer, a scheduler, a collection orchestrator, the collectors, the "
  "detectors, the findings engine, an owner resolver and a price book, all above a data-access layer. State lives in an SQL database (SQLite for development, "
  "PostgreSQL for deployment) beside a credential store. The right-hand side is the customer's Azure subscription.")
r.figure(str(FIG / "fig_architecture.png"), "CloudPulse architecture with the Azure credential and data flows", 15.5)
P("**Credential flow.** An operator runs a set of Azure CLI scripts once. They create an app registration and service principal and assign the two read-only "
  "roles at subscription scope (step 0 in Figure 1). On each synchronisation the collector presents the tenant identifier, client identifier and client secret to "
  "Microsoft Entra ID, receives a bearer token (steps 5 and 6), and calls Azure Resource Manager (steps 7 and 8). Azure RBAC authorises every call against the "
  "assigned roles, so a stolen secret could read cost and inventory but could not create, modify or delete anything. Three sign-in modes are supported: the "
  "developer's own Azure CLI session on a laptop, a service principal anywhere, and a managed identity on Azure App Service, in which case no secret exists at all.")
P("**Data sources.** The collector reads daily cost by service and resource from Cost Management; disks, public IP addresses, snapshots and virtual machines "
  "(including power state) from Resource Graph; hourly CPU and network metrics for fourteen days from Azure Monitor; the creator of each resource from the Activity "
  "Log; and recommendations from Azure Advisor. A custom REST client retries on throttling (HTTP 429) and server errors and follows result paging. Prices for "
  "idle resources come from the public Azure Retail Prices API, with a local cache.")

# ----------------------------------------------------------------- IV
H1("IV. Methods")
H2("A. Spend anomaly detection")
P("Let x_t be the cost on day t. The baseline B_t is the same weekday in the previous four weeks when at least three of those days have billing data, "
  "and the previous fourteen days otherwise. With m_t the median of B_t and MAD_t its median absolute deviation, the spread and the robust score are")
EQ("s_t = max(1.4826 · MAD_t, 0.05 · m_t, 0.01),    z_t = (x_t − m_t) / s_t", 1)
P("A day is flagged when z_t > 3.5 and the excess x_t − m_t is at least max(1, 0.2 · m_t). The floors on s_t stop a perfectly flat history from producing a "
  "zero spread, and the excess condition suppresses statistically significant but financially trivial spikes. At least seven billed days of history are required. "
  "The cause of a flagged day is explained by comparing each service's cost that day with its own median on the baseline days; the positive differences are "
  "normalised to shares that add to 100%. A spike is classed as ongoing when the following two days both exceed m_t + 0.5 (x_t − m_t); an ongoing spike "
  "is projected at 30.4 times the daily excess per month, and a one-off spike is reported at its own excess. Confidence is min(0.95, 0.55 + 0.05 (z_t − 3.5)).")
H2("B. Month-end and budget forecasting")
P("Daily cost is first divided by a weekday factor, then smoothed with Holt's method:")
EQ("ℓ_t = α y_t + (1 − α)(ℓ_{t−1} + b_{t−1}),    b_t = β (ℓ_t − ℓ_{t−1}) + (1 − β) b_{t−1}", 2)
P("The pair (α, β) is chosen from the grid α ∈ {0.2, 0.4, 0.6, 0.8}, β ∈ {0.05, 0.1, 0.2} by minimising the one-step-ahead squared error. The h-day forecast is "
  "ℓ_t + h b_t, multiplied back by the weekday factor, and an 80% interval uses 1.2816 times the residual standard deviation. The projected month-end "
  "total is compared with the workspace budget, and a budget-risk finding is raised when the projection exceeds it; the predicted crossing day is shown on the chart.")
H2("C. Idle and oversized machines")
P("From at least 48 hourly Azure Monitor points, CloudPulse computes the 95th percentile of hourly CPU and of network traffic. A machine is idle when its "
  "CPU p95 is below 5% and network p95 below 5 MB per hour, and oversized when CPU p95 is below 20% and the peak is below 80%. Confidence is 0.85 with "
  "seven or more days of data and 0.65 with less; oversized verdicts are reduced by 0.15 because memory is not measured. An oversized finding proposes the next "
  "smaller size from the same series. A percentile rather than the mean prevents a brief batch job from hiding an otherwise idle machine.")
H2("D. Rule checks")
P("Four checks use resource state directly: a managed disk whose state is Unattached; a static public IP address with no association; a snapshot whose source disk no "
  "longer exists or that is older than a configurable age; and a virtual machine that is stopped but not deallocated, whose impact is its compute price plus the "
  "price of its disks. Each check records the rule that fired as evidence, and each proposes an Azure CLI command, with a backup step where deletion is irreversible.")
H2("E. Priority score")
P("Each finding receives a score between 0 and 100:")
EQ("S = 100 · (0.6 · I + 0.4 · W) · C · A",  3)
P("where I = min(1, log10(1 + impact) / log10(1 + 1000)) is a logarithmic impact term (impact in currency units per month; governance findings such as untagged spend "
  "are weighted down), W is a severity weight (critical 1.0, high 0.8, medium 0.55, low 0.3), C is the confidence, and A = 1 + min(0.3, days_open / 100) lets "
  "neglected findings rise. Scores of at least 70, 45 and 25 map to P1, P2 and P3, and the rest to P4. The logarithm stops a single very large item from drowning "
  "everything else (Figure 2).")
r.figure(str(FIG / "fig_priority.png"), "Priority score against monthly impact (confidence 0.9, new finding), produced by the implemented function", 11.5)
H2("F. Ownership and lifecycle")
P("The owner of a resource is resolved in order from the Azure Activity Log (the identity that created it), then from an owner tag, then from a manual assignment; "
  "when none exists the finding is shown as having no owner rather than guessed. An owner is matched to a CloudPulse user where the e-mail address agrees. "
  "Findings move through the states of Figure 3: open, assigned, in progress, resolved and verified, with dismissal (a reason is required) and snoozing "
  "from any active state. A resolved finding returns to open if the resource is detected again, and a verified saving is withdrawn.")
r.figure(str(FIG / "fig_lifecycle.png"), "Finding lifecycle, with automatic and manual transitions", 11.0)
H2("G. Verification of savings")
P("When a finding is marked fixed on day d, CloudPulse compares the average daily cost of the affected resource over the seven days before d with the days after d "
  "(excluding d, which may be billed partly). Missing cost days count as zero only up to the last day for which the workspace has any billing data, because "
  "Azure publishes cost with a delay of up to a day. No result is produced until at least three days after the fix are available. The realised monthly saving is "
  "the daily drop multiplied by 30.4, and the ratio of realised to estimated saving gives an estimate-accuracy figure for the workspace.")

# ----------------------------------------------------------------- V
H1("V. Implementation")
P("The back end is written in Python with FastAPI and SQLAlchemy, with APScheduler running a synchronisation every six hours. The interface is plain HTML, CSS and "
  "JavaScript with hand-written SVG charts and no front-end framework, which keeps the whole product small enough to read. Sessions use an HttpOnly cookie with a "
  "CSRF header and login rate limiting; three roles (administrator, customer owner, customer viewer) and a read-only demo identity control access; every "
  "sensitive action is written to an audit log. Stored cloud secrets are encrypted with Fernet; passwords are hashed with scrypt. A FOCUS importer aggregates line "
  "items to one row per provider, service and day, keeping the share of cost that carried tags so that untagged spend can be reported. Table 1 lists the components.")
r.table("Main components and technologies",
        ["Component", "Technology", "Purpose"],
        [["API and server", "Python, FastAPI, Uvicorn", "REST endpoints, authentication, role checks"],
         ["Storage", "SQLAlchemy; SQLite or PostgreSQL", "Costs, findings, users, audit log, encrypted credentials"],
         ["Scheduler", "APScheduler", "Synchronisation every six hours"],
         ["Azure access", "REST client, azure-identity", "ARM, Cost Management, Resource Graph, Monitor, Activity Log"],
         ["Bill import", "FOCUS CSV importer", "Provider-neutral spend analytics"],
         ["Secrets", "Fernet, scrypt", "Encrypted cloud secrets, hashed passwords"],
         ["Interface", "HTML, CSS, JavaScript, SVG", "Dashboards, findings, owners, savings, audit"],
         ["Quality", "pytest, GitHub Actions, Docker", "27 automated tests, CI, deployment image"]],
        [3.2, 5.0, 7.7], size=10, center=False)

# ----------------------------------------------------------------- VI
H1("VI. Evaluation")
P("We evaluate three things: that the implemented system behaves as specified on real billing data, that the detector and forecaster behave well on controlled series "
  "with known answers, and what the evaluation cannot tell us.")
H2("A. Functional evaluation on a public bill")
P("The demonstration workspace is built on the FinOps Foundation's anonymised FOCUS sample bill (100,000 line items, licensed CC BY 4.0), aggregated to 1,166 "
  "daily service rows, with September 2024 as the reporting month. The reported spend is $2,829.99. The anomaly detector flagged exactly one day, "
  "24 September 2024: spend was $169.26 against a same-weekday median of $73.55, an excess of $95.71 (2.3 times the usual) with a robust score of 7.9 against the threshold "
  "of 3.5, and 99.1% of the increase came from one compute service. The next two days stayed high, so the spike was classed as ongoing. Against a budget of $2,600 the "
  "forecast crossed the limit on 28 September (109% of budget), the highest-scoring finding (75, band P1). The resource findings in this workspace are scripted example records "
  "that run through the same scoring and verification code as a live workspace: 12 findings in total, $262.94 a month still open and $33.44 a month verified, with an "
  "estimate accuracy of 94%. These figures show that the pipeline is internally consistent (open and owned stages add up to the headline total); they are not evidence "
  "about real savings. The 27 automated tests cover the statistics, scoring, lifecycle, verification, roles, the importer, security checks and the static interface, and all pass.")
H2("B. Simulation of the detector")
P("Real billing data with ground-truth anomalies is hard to obtain, so we used a seeded simulation (Python random seeds fixed in the released script). A daily series of 120 "
  "days has a base level of 100, a 0.2% daily trend, weekends 22% cheaper, and log-normal noise with σ = 0.08 (quiet) or 0.15 (noisy). One spike of size k times "
  "the day's value is injected at a random day from 45 to 116, 400 trials per setting, and a detection counts only if the injected day is flagged. We compare the "
  "CloudPulse detector with the textbook rule 'value above the mean plus three standard deviations of the previous 14 days'. False alarms are flagged days per 100 clean days "
  "over 300 series.")
rows = []
for sg in ("0.08", "0.15"):
    d = R["detect"][sg]; f = R["false_alarms"][sg]
    for k in ("1.25", "1.5", "2.0", "3.0"):
        rows.append([sg, f"{k}×", f"{100*d[k]['cloudpulse']:.1f}%", f"{100*d[k]['naive']:.1f}%"])
r.table("Detection rate of injected spikes (400 trials per row)", ["Noise σ", "Spike size", "CloudPulse", "Mean + 3σ rule"], rows, [3.2, 3.6, 4.2, 4.9], size=10)
P(f"Table 2 gives the results. CloudPulse detected more injected spikes than the baseline at every size below 3× and equal at 3×, and the gap is largest for moderate spikes: at 1.5 times the usual cost and σ = 0.08 "
  f"it found {100*R['detect']['0.08']['1.5']['cloudpulse']:.0f}% against {100*R['detect']['0.08']['1.5']['naive']:.0f}%. Both methods found essentially all spikes of three times "
  f"the usual cost. The price is false alarms: CloudPulse flagged {R['false_alarms']['0.08']['cloudpulse']:.2f} and {R['false_alarms']['0.15']['cloudpulse']:.2f} days per 100 "
  f"clean days at σ = 0.08 and 0.15, against {R['false_alarms']['0.08']['naive']:.2f} and {R['false_alarms']['0.15']['naive']:.2f} for the baseline. The same-weekday baseline has only four "
  "values, so its estimate of spread is itself noisy; the financial-significance condition (excess of at least 20%) removes the smallest of these, and raising the threshold "
  "above 3.5 is the obvious tuning knob for noisy workloads. We report the trade-off rather than a single score because the right operating point depends on how costly a "
  "false alarm is to the owner.")
H2("C. Simulation of the forecaster")
P("We generated 200 series of 150 days with a 0.4% daily trend, weekend effect and σ = 0.08 noise, and at 2,200 origins forecast the cost seven days ahead from a 60-day history. "
  "Holt with weekday factors (the CloudPulse method) was compared with a seven-day moving average and with a naive forecast equal to the last observed day, which for a "
  "seven-day horizon is the value on the same weekday of the previous week (Table 3).")
r.table("Seven-day-ahead forecast error (mean absolute percentage error, 2,200 origins)",
        ["Method", "MAPE"],
        [["Holt with weekday factors (CloudPulse)", f"{R['forecast']['holt+weekday']:.2f}%"],
         ["Seven-day moving average", f"{R['forecast']['ma7']:.2f}%"],
         ["Same-weekday naive (last observation)", f"{R['forecast']['naive']:.2f}%"]], [9.0, 3.5], size=10)
P("Holt with weekday factors reduced the error of the moving average by 13%, but did not beat the same-weekday naive forecast on this stationary-noise series. That is an honest "
  "limit of the method at a short horizon: its advantage is not accuracy over a one-week lag but that it extrapolates the trend, produces an interval, and projects the whole "
  "month for the budget check, none of which the naive forecast does.")
H2("D. Threats to validity")
P("The evaluation has clear limits. The bill used for the functional results is a public sample, not our own workload. The resource-level findings in the demonstration are "
  "scripted, so the $33.44 verified saving demonstrates the mechanism, not realised savings. The simulation uses a simple generating process; real bills have step changes, "
  "monthly commitments and holidays. The 1.5 times, 2.0 times and similar spike sizes are our choices. We have not run a field study with an organisation's production "
  "subscription, and we have not compared against commercial tools. A scripted Azure environment that plants real waste exists for such validation and is described in the "
  "project documentation, but its results are not part of this paper.")

# ----------------------------------------------------------------- VII
H1("VII. Conclusion and Future Work")
P("CloudPulse shows that a small system built on inspectable methods can carry a cost problem from signal to verified saving while holding only read-only cloud permissions. "
  "Its distinguishing choices are accountability (a named creator for each finding), honesty about savings (counted only after the bill confirms them) and safety (a "
  "service principal that cannot change the environment). The robust same-weekday detector finds moderate spikes that a mean-and-deviation rule misses, at the cost of more "
  "false alarms, and Holt forecasting with weekday factors improves on a moving average while remaining easy to explain.")
P("Future work includes a field study on live subscriptions with real ground truth; tuning of the detector threshold per workload and a comparison with seasonal models; "
  "GPU-aware checks, because the present idle verdict uses CPU and network only and could misjudge a machine that trains models on its GPU; categorisation of AI and machine-learning "
  "spend with its own budget; resource-level checks for AWS and Google Cloud; and a natural-language layer that explains findings, kept separate from detection so "
  "that every flagged item remains explainable.")
H1("Declarations")
P("**Data and code availability.** The bundled sample bill is the FinOps Foundation's public FOCUS sample (CC BY 4.0). The simulation script and the results file used in "
  "Section VI are part of the project source, which is available from the authors [add repository URL before publishing]. **Competing interests.** The authors declare no competing "
  "interests. **Funding.** This work received no external funding.", size=10.5)

# ----------------------------------------------------------------- refs
H1("References")
refs = [
 "M. Armbrust et al., \"A view of cloud computing,\" Communications of the ACM, vol. 53, no. 4, pp. 50–58, 2010.",
 "J. R. Storment and M. Fuller, Cloud FinOps: Collaborative, Real-Time Cloud Financial Management, 2nd ed. Sebastopol, CA: O'Reilly Media, 2023.",
 "Cloud Custodian Project, \"Cloud Custodian: rules engine for cloud security, cost optimization and governance,\" https://cloudcustodian.io.",
 "FinOps Foundation, \"FinOps Open Cost and Usage Specification (FOCUS),\" https://focus.finops.org.",
 "C. Leys, C. Ley, O. Klein, P. Bernard and L. Licata, \"Detecting outliers: Do not use standard deviation around the mean, use absolute deviation around the median,\" Journal of Experimental Social Psychology, vol. 49, no. 4, pp. 764–766, 2013.",
 "P. J. Rousseeuw and C. Croux, \"Alternatives to the median absolute deviation,\" Journal of the American Statistical Association, vol. 88, no. 424, pp. 1273–1283, 1993.",
 "B. Iglewicz and D. C. Hoaglin, How to Detect and Handle Outliers. Milwaukee, WI: ASQC Quality Press, 1993.",
 "C. C. Holt, \"Forecasting seasonals and trends by exponentially weighted moving averages,\" International Journal of Forecasting, vol. 20, no. 1, pp. 5–10, 2004 (reprint of the 1957 Office of Naval Research memorandum).",
 "R. J. Hyndman and G. Athanasopoulos, Forecasting: Principles and Practice, 3rd ed. Melbourne: OTexts, 2021.",
 "J. H. Saltzer and M. D. Schroeder, \"The protection of information in computer systems,\" Proceedings of the IEEE, vol. 63, no. 9, pp. 1278–1308, 1975.",
 "Microsoft, \"What is Azure role-based access control (Azure RBAC)?\" Microsoft Learn documentation, https://learn.microsoft.com/azure/role-based-access-control/overview.",
 "D. Hardt, Ed., \"The OAuth 2.0 Authorization Framework,\" RFC 6749, Internet Engineering Task Force, 2012.",
 "Fernet specification, https://github.com/fernet/spec.",
 "C. Percival and S. Josefsson, \"The scrypt password-based key derivation function,\" RFC 7914, Internet Engineering Task Force, 2016.",
]
for i, t in enumerate(refs, 1):
    p = r.para(f"[{i}]  {t}", align="j", size=10, spacing=1.1, after=3, indent=0.9)
    p.paragraph_format.first_line_indent = Cm(-0.9)

out = HERE / "output"; out.mkdir(exist_ok=True)
r.save(out / "CloudPulse_Research_Paper.docx")
subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out), str(out / "CloudPulse_Research_Paper.docx")],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
print(subprocess.run(["pdfinfo", str(out / "CloudPulse_Research_Paper.pdf")], capture_output=True, text=True).stdout)
