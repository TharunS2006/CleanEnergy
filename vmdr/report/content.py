"""Chapters of the VM Availability and Disaster Recovery report. Every measured number is read from bench_results.json."""
import json, math, pathlib, sys
HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
R = json.load(open(ROOT / "bench_results.json"))
A = "assets/"
ST = R["strategies"]; SP = R["spread"]; FO = R["failover_sweep"]; MT = R["mttr_sweep"]; TI = {t["key"]: t for t in R["tiers"]}; PL = R["planner"]
from vmdr import avail, sim, dr, backup


def loc(path):
    return len((ROOT / path).read_text(encoding="utf-8").splitlines())


def trim_empty(r):
    body = r.doc.element.body
    while True:
        kids = [k for k in body if not k.tag.endswith("sectPr")]
        last = kids[-1]
        if last.tag.endswith("}p") and not "".join(last.itertext()).strip() and not last.xpath(".//w:drawing | .//w:br"):
            body.remove(last)
        else:
            break


def H1(r, text, n):
    if n > 1:
        trim_empty(r)
    p = r.h(1, text)
    if n > 1:
        p.paragraph_format.page_break_before = True
    return p


def hm(minutes):
    return f"{minutes / 60:.1f} h" if minutes >= 120 else f"{minutes:.1f} min"


def chapter1(r):
    H1(r, "1. INTRODUCTION", 1)
    r.h(2, "1.1  Background")
    r.para("Most services that people use every day, from online shops to college portals, run on virtual machines. A virtual machine (VM) is a "
           "software computer that runs on a physical host, a host sits in a data centre called an availability zone, and several zones make up a "
           "region of a cloud provider. Barham et al. [6] described the hypervisor technique that made this practical, and Clark et al. [7] showed that a "
           "running VM can be moved from one host to another with only a very short pause. Every layer of this stack can fail: a host can break, a "
           "zone can lose power or cooling, and in rare cases a whole region can become unavailable because of a natural disaster, a large "
           "network failure or a faulty software release [4].")
    r.para("The quality that users notice is **availability**, the fraction of time the service works. It is usually stated in \"nines\": 99.9% "
           "allows about 8.8 hours of downtime a year, 99.99% about 53 minutes. Two other numbers matter when something does fail. The **recovery "
           "time objective (RTO)** is how long the service may stay down after a disaster. The **recovery point objective (RPO)** is how much recent data the "
           "business can afford to lose, measured in time: an RPO of 15 minutes means the newest 15 minutes of data may be lost. Cloud providers publish service "
           "level agreements that depend on the way a customer deploys: for example Microsoft documents different availability figures for a "
           "single VM, for several VMs in one availability set and for VMs spread over availability zones [10]. The customer is responsible for choosing "
           "the design, and the cost grows with every copy of a VM and every copy of the data.")
    r.table("Table 1.1: What each layer of the stack can lose and what protects against it",
            ["Failure", "Typical duration", "How often", "Protection"],
            [["Host (physical server)", "hours", "every few months per host", "automatic restart on another host, a standby VM, or a second active VM"],
             ["Availability zone", "hours", "years apart", "a second VM in another zone"],
             ["Region", "days", "decades apart", "a copy of the service and its data in another region (disaster recovery)"],
             ["Data (deletion, corruption, ransomware)", "n/a", "unpredictable", "backups kept apart from the VM"]],
            widths=[3.8, 2.6, 3.4, 5.2], size=10)
    r.h(2, "1.2  Problem Statement")
    r.para("A team that has to choose a deployment faces questions that have numerical answers but are usually answered by habit. How much downtime will "
           "a single VM have in a year? How much does a second VM in the same zone help, and how much in another zone? Is automatic restart enough? How much "
           "does a slow failover cost? When is a second region worth its price, and which of the standard disaster-recovery patterns meets the "
           "RTO and RPO that the business asked for? A spreadsheet can answer the first few questions with formulas, but it cannot handle failover delays, "
           "waiting for repairs, or failures that overlap in time, which are exactly the cases that decide the outcome.")
    r.para("The problem addressed here is to build a tool that (i) computes availability from first principles, (ii) simulates random failures of hosts, "
           "zones and regions and compares deployment designs on the same failures, (iii) models disaster-recovery tiers with their RTO, RPO and cost, and "
           "(iv) recommends the cheapest design that meets stated targets, while (v) being checked against known mathematical results so that its numbers can be trusted.")
    r.h(2, "1.3  Motivation")
    r.para("Three observations motivated the project. First, the rules of thumb contradict each other: redundancy is said to raise availability, yet the "
           "residual downtime of a well-built design is dominated by rare, long events that redundancy inside a region cannot touch. A simulation shows which "
           "event dominates. Second, availability, RTO, RPO and cost pull in different directions, and a planner that lists every option with the reason it passes or fails "
           "makes the trade-off visible. Third, a reliability model is only useful if it can be validated; the simple structure of the problem allows the simulator to be compared "
           "with exact formulas and with a Markov model, which most student projects on cloud reliability do not attempt.")
    r.h(2, "1.4  Scope")
    r.para("The tool is a model, not a connection to a real cloud. It treats hosts, zones and regions as independent components that fail and are repaired at random with given mean times. "
           "It models six deployment designs and four disaster-recovery tiers, backup schedules and restore times, and the planner described above. It does not call cloud "
           "provider APIs, does not model correlated failures other than the zone and region hierarchy, does not model software faults, network partitions or capacity "
           "shortages, and treats the recovery times and costs of the DR tiers as input assumptions (Table 5.3) rather than provider prices. The limits and ways to remove them are discussed in Section 7.")


def chapter2(r):
    H1(r, "2. OBJECTIVES", 2)
    r.para("The main objective is to design and implement a tool that calculates, simulates and plans the availability and disaster recovery of virtual machines, and to "
           "evaluate it against known mathematical results. The specific objectives are:")
    r.bullets(["To implement the mathematics of availability: MTBF and MTTR, nines, series and parallel systems, k-out-of-n systems, and an exact Markov model of an active-passive pair.",
               "To build a Monte Carlo simulator in which hosts, zones and regions fail and are repaired at random, and in which six deployment designs are evaluated on the same failures.",
               "To model failover for an active-passive pair and the takeover by a DR region, including the case in which the standby fails during the switch.",
               "To model four disaster-recovery tiers with their recovery time, data loss and cost, and to report how often a takeover is needed.",
               "To calculate backup data age and restore time for a given schedule and data size.",
               "To provide a planner that returns the cheapest design meeting an availability target, an RTO and an RPO, and explains why each rejected design fails.",
               "To validate the simulator against the closed-form results and to offer a command-line interface and a browser interface."])
    r.table("Table 2.1: Functional requirements",
            ["ID", "Requirement"],
            [["FR1", "Compute the availability, nines and yearly downtime of a component from its MTBF and MTTR, and of redundant groups"],
             ["FR2", "Simulate host, zone and region failures for a chosen number of years with a fixed random seed"],
             ["FR3", "Evaluate single VM, auto-restart, active-passive (one or two zones), active-active and active-active with a DR region on the same failures"],
             ["FR4", "Report availability, downtime per year, incidents per year and longest incident for every design"],
             ["FR5", "Model DR takeover with the recovery time, data loss and cost of each tier"],
             ["FR6", "Compute the average age of the newest good backup, its 99th percentile and the restore time"],
             ["FR7", "Recommend the cheapest design that satisfies the targets and give the reason for every rejected one"],
             ["FR8", "Reject wrong input (negative repair time, empty targets) with a clear message"]],
            widths=[1.6, 13.4], size=10.5)
    r.table("Table 2.2: Non-functional requirements",
            ["Requirement", "How it is met"],
            [["Correctness", "Simulation compared with closed forms and a Markov model; 39 automated tests"],
             ["Repeatability", "Every simulation uses a seed; the same seed gives the same result"],
             ["Fair comparison", "All designs are judged on the same simulated failures (common random numbers)"],
             ["Portability", "Python standard library only"],
             ["Speed", "Twenty thousand simulated years for all six designs in about two seconds"]],
            widths=[3.6, 11.4], size=10.5)


def chapter3(r):
    H1(r, "3. TOOLS AND TECHNOLOGIES", 3)
    r.para("The tool is written in Python and uses only the standard library, so that each model can be read next to its formula. Table 3.1 lists what was used.")
    r.table("Table 3.1: Tools and technologies used",
            ["Item", "Tool", "Purpose"],
            [["Language", "Python 3.10 or newer (developed and tested on 3.13)", "Mathematics, simulation, planner, interfaces"],
             ["Libraries", "Standard library only: `random`, `heapq`, `dataclasses`, `math`, `http.server`, `json`, `unittest`", "Random failures, event timers, server, tests"],
             ["Browser interface", "One HTML file with CSS and plain JavaScript", "Four tabs: availability, strategies, planner, backups"],
             ["Server", "`http.server.ThreadingHTTPServer`", "JSON endpoints used by the page"],
             ["Testing", "`unittest`", "39 automated tests"],
             ["Charts for this report", "matplotlib", "Figures 6.1 to 6.6 (not needed to run the tool)"],
             ["Editor and shell", "Visual Studio Code, PowerShell or any terminal", "Development"]],
            widths=[3.0, 6.0, 6.0], size=10)
    r.h(2, "3.1  Running the project")
    r.para("The project is a folder named `vmdr`. No installation is needed. From inside the folder:")
    r.code("""
python -m unittest discover -s tests          # the 39 automated tests (a few seconds)
python -m vmdr.cli demo                       # every part of the tool with default values
python -m vmdr.cli avail --mtbf 2000 --mttr 4
python -m vmdr.cli compare --years 5000
python -m vmdr.cli plan --target 0.9999 --rto 60 --rpo 15
python -m vmdr.cli backup --interval 1440 --success 0.98
python -m vmdr.server 8000                    # browser interface at http://127.0.0.1:8000
python bench.py                               # the experiments of Chapter 6
""")


def chapter4(r):
    H1(r, "4. ARCHITECTURE DIAGRAM", 4)
    r.para("The tool has four layers (Figure 4.1). The presentation layer is the command line, the browser page and the HTTP server behind the page. The planner "
           "holds the DR tiers and the function that chooses the cheapest design. The simulation engine generates random failures, evaluates the six strategies "
           "on them and contains the state machine of a failover. At the bottom, the mathematics module holds the closed-form results that the simulation is checked against, "
           "and the backup module holds the data-age and restore-time calculations. A layer calls only the layer below it, so the engine can be tested without an interface.")
    r.figure("diagrams/fig41.png", "Figure 4.1: Layers of the VM Availability and DR tool", width_cm=14.0)
    r.table("Table 4.1: Module responsibilities",
            ["File", "Lines", "Responsibility"],
            [["`vmdr/avail.py`", loc("vmdr/avail.py"), "Availability formulas and the Markov model of an active-passive pair"],
             ["`vmdr/sim.py`", loc("vmdr/sim.py"), "Failure generator, interval arithmetic, six strategies, failover state machine, DR takeover"],
             ["`vmdr/dr.py`", loc("vmdr/dr.py"), "DR tiers, data-loss sampling, DR event statistics, planner"],
             ["`vmdr/backup.py`", loc("vmdr/backup.py"), "Backup data age, percentile and restore time"],
             ["`vmdr/cli.py`, `vmdr/server.py`", loc("vmdr/cli.py") + loc("vmdr/server.py"), "Command line and HTTP server"],
             ["`web/index.html`", loc("web/index.html"), "Browser page"],
             ["`tests/test_vmdr.py`", loc("tests/test_vmdr.py"), "39 automated tests"],
             ["`bench.py`", loc("bench.py"), "Experiments of Chapter 6"]],
            widths=[5.4, 1.5, 8.1], size=10)
    r.h(2, "4.1  The deployment that is modelled")
    r.para("Figure 4.2 shows the deployment that the tool models. The primary region has two availability zones, each with a host that can run the VM. A load balancer or "
           "failover manager sends users to a working VM. The DR region holds a standby copy of the service whose readiness depends on the tier, and a backup vault holding "
           "copies of the disks. Data reaches the DR region by asynchronous replication and by backups. The strategies of Section 5.3 use different parts of this picture: a single "
           "VM uses one host in one zone; an active-passive pair uses two hosts; an active-active pair uses one host in each zone; the DR strategy adds the other region.")
    r.figure("diagrams/fig42.png", "Figure 4.2: The deployment that is modelled", width_cm=14.0)


def chapter5(r):
    H1(r, "5. METHODOLOGY", 5)
    r.h(2, "5.1  Overall approach")
    r.para("The method combines three ways of looking at the same question. **Closed-form mathematics** gives exact answers for the simple cases, and the **Markov model** gives an exact answer for "
           "the active-passive pair. **Monte Carlo simulation** handles everything else, and is validated by reproducing the exact answers where they exist. The **planner** uses the simulation to rank designs "
           "against stated targets. This ordering is deliberate: a simulator whose answer is not checked against anything is only a random number generator, so the first results in Chapter 6 are the validation.")
    r.h(2, "5.2  Availability mathematics")
    r.para("A repairable component alternates between working for a mean time MTBF (mean time between failures) and being repaired for a mean time MTTR (mean time to repair). "
           "Over a long time its availability is **A = MTBF / (MTBF + MTTR)**; only the two means matter, not the shape of the distributions [1][2]. For a host with MTBF = 2,000 hours and MTTR = 4 hours, "
           "A = 0.998004, which is 2.70 nines and about 17.5 hours of downtime a year. Components combine in two ways. In **series** all must work, so availabilities multiply: a VM needs its "
           "host and its zone and its region. In **parallel** at least one must work, so unavailabilities multiply: two independent copies each with A = 0.998 give 1 − 0.002² = 0.999996. "
           "A group in which at least *k* of *n* identical copies must work has availability the sum over *i* from *k* to *n* of C(n, i) A^i (1 − A)^(n − i).")
    r.para("Parallel redundancy has a limit that the formulas show clearly: it works only for failures that are independent. Two VMs in the same zone share the zone, and two VMs in the same region share the region, "
           "so the probability of a zone or region failure appears in series with the redundant group and sets a floor that no number of VMs can lower. The simulator reproduces this effect "
           "with a hierarchy of hosts, zones and regions (Section 5.3).")
    r.para("An active-passive pair, in which one VM serves and the other waits, cannot be written with series and parallel formulas because of the failover delay and the fact that the roles change. "
           "Under the assumption that failure, repair and failover times are exponential, the pair is a continuous-time Markov chain with four states (Figure 5.1): both up (0), standby down (1), active down and switching (2), "
           "both down (3). The service is down in states 2 and 3. The long-run probabilities satisfy the balance equations of the chain, which the program solves by Gaussian elimination, and the unavailability is "
           "π₂ + π₃. For a pair with MTBF 2,000 h, MTTR 4 h and a failover of 2 minutes this gives 2.05 × 10⁻⁵, about 10.8 minutes a year [11].")
    r.figure("diagrams/fig51.png", "Figure 5.1: Active-passive pair as a four-state Markov chain", width_cm=14.0)
    r.h(2, "5.3  Monte Carlo simulation")
    r.para("A **world** is generated first: for every host, zone and region the simulator draws alternating up and down periods, with exponentially distributed lengths of mean MTBF and MTTR, until the simulated time is used up [3]. "
           "The result is a list of down intervals for each component. Because each design is then evaluated on the *same* world, the difference between two designs comes from the design and not from luck (the method of common random numbers). "
           "Each design is a rule that turns the component intervals into the intervals in which the service is down, using interval arithmetic: the union of two lists is the time when either is down, the intersection is the time when both are.")
    r.table("Table 5.1: The six designs and how the service-down intervals are built",
            ["Design", "Service is down when"],
            [["Single VM", "its host, its zone or the region is down (union)"],
             ["Single VM with automatic restart", "like a single VM, but a host failure lasts only the restart time (6 minutes) instead of the repair time; zone and region failures are unaffected. Assumes spare capacity on other hosts."],
             ["Active-passive, one zone", "the failover state machine of Section 5.4 on two hosts in the same zone, or the region is down"],
             ["Active-passive, two zones", "the same state machine with the two VMs in different zones, or the region is down"],
             ["Active-active, two zones", "both instances are down at the same time (intersection), or the region is down; the load balancer is assumed to react at once"],
             ["Active-active plus DR region", "both instances are down, or a region outage has lasted long enough that the DR takeover is in progress (Section 5.5)"]],
            widths=[4.6, 10.4], size=10)
    r.para("The default parameters of the model are in Table 5.2. They are plausible orders of magnitude for a small cloud deployment, not measurements of any provider, and every one can be changed from the command line or the browser.")
    r.table("Table 5.2: Default parameters of the failure model",
            ["Parameter", "Value", "Meaning"],
            [["Host MTBF, MTTR", "2,000 h, 4 h", "a host fails about every 83 days and takes four hours to repair"],
             ["Zone MTBF, MTTR", "17,520 h, 3 h", "a zone outage about every two years, lasting three hours"],
             ["Region MTBF, MTTR", "175,200 h, 48 h", "a regional disaster about every twenty years, lasting two days"],
             ["Restart time", "6 min", "time for HA to detect a dead host and boot the VM elsewhere"],
             ["Failover time", "2 min", "time to switch from the active VM to the standby"],
             ["Detection time", "5 min", "time to notice a region outage and decide to fail over"]],
            widths=[4.0, 3.2, 7.8], size=10)
    r.h(2, "5.4  The failover state machine")
    r.para("For an active-passive pair the service-down intervals are not a simple combination of the two VMs' intervals, because the standby takes over only after a delay and then the roles stay swapped. "
           "The simulator therefore processes the failure and repair events of the two VMs in time order together with failover timers. When the active VM goes down and the other is up, the service is down and a timer "
           "of the failover time starts; when it ends, the other VM becomes active. If the target fails before the timer ends, the switch is cancelled. If the original VM comes back first, the switch is "
           "abandoned and the service resumes at once. If both are down, the service waits for the first repair and then starts a switch if it was the standby that returned. The old active VM, once repaired, "
           "simply becomes the standby (there is no fail-back). Six hand-checked cases in the tests cover each branch.")
    r.h(2, "5.5  Disaster-recovery tiers")
    r.para("A region outage is survived by moving the service to the DR region. For each outage of the primary region the simulator checks whether it lasts longer than the takeover time T = detection time + the tier's restore time. "
           "If it does not, nothing is moved and the service is down for the whole outage. If it does, the service is down for T and then runs in the DR region until the primary returns; "
           "if the DR region is itself down at the moment of takeover, the service waits for the first recovery, and if it fails while carrying the service the downtime is counted. "
           "At every takeover some recent data is lost, because it had not yet reached the DR region. For the asynchronous tiers the amount is exponentially distributed with the replication lag as its mean; for "
           "backup and restore it is uniform over the backup interval; asynchronous replication of VMs is described in [8] and the tier patterns in [9]. The four tiers follow the patterns described by cloud providers [9].")
    r.table("Table 5.3: Disaster-recovery tiers (model assumptions)",
            ["Tier", "Restore time", "Data lost per takeover (mean)", "Extra cost", "Description"],
            [[t.name, f"{t.restore_minutes:g} min", f"{t.rpo_mean_minutes:g} min", t.extra_cost, t.note] for t in dr.TIERS.values()],
            widths=[2.8, 1.9, 2.4, 1.5, 6.4], size=9)
    r.para("The restore times, the replication lags and the costs are assumptions of the model, stated in the style of provider guidance. They are inputs, not findings, and should be replaced with a "
           "provider's own figures when a real design is evaluated. Cost is measured in VM equivalents, with one VM costing 1.0; the primary site of two VMs and a load balancer costs 2.1, and the tier adds its extra cost on top.")
    r.h(2, "5.6  Backups")
    r.para("A backup taken every *I* minutes that always succeeds leaves, at a random moment, a newest copy that is on average *I*/2 old and at worst *I* old. If each backup succeeds only with probability *p*, "
           "the age adds one interval for every failed backup in a row, so the mean age is *I* × (1/*p* − 1/2) and the age that is exceeded one time in 100 is (*k* + 1) × *I*, where *k* is the "
           "smallest number of failures in a row whose probability is at most 1%. The restore time is the time to copy the data (size ÷ throughput) plus the boot and checking time, taken as 20 and 10 minutes. "
           "A Monte Carlo check of the mean is included in the tests.")
    r.h(2, "5.7  The planner")
    r.para("The planner evaluates all designs on one simulated world: the five designs without a DR region and the DR strategy with each of the four tiers. For each it records availability, cost, the recovery time "
           "for a region disaster and the data loss. A design without a DR region can survive a region disaster only by waiting for the region to be repaired, so its recovery time is the region's repair time and it has no copy of the data outside the region; "
           "it therefore fails any RTO or RPO shorter than that. A design is accepted only if it meets the availability target and every limit that was given; the cheapest accepted design is recommended, and "
           "every rejected design carries the list of limits it breaks. If nothing is accepted the planner says so rather than choosing the nearest.")
    r.h(2, "5.8  Testing methodology")
    r.para("Five kinds of test were used. **Mathematics**: known values (a 99.99% target allows 52.56 minutes a year, 2-of-3 with A = 0.9 is 0.972) and the limits of the Markov model (never better than ideal active-active, worse as failover slows). "
           "**State machine**: six hand-calculated cases for failover, including the standby failing after the switch, the target failing during the switch, and an outage still open at the end of the simulation. "
           "**DR**: takeover timing, the short outage that causes no takeover, the DR region being down, and the sample means of data loss. **Validation against theory**: the simulated unavailability of a single VM, of an active-active pair and of an "
           "active-passive pair must be within 4%, 5% and 8% of the exact value on 15,000 to 30,000 simulated years. **Planner and interfaces**: the recommendations for four known cases, a reason for every rejection, and the HTTP endpoints, "
           "including the 400 reply for invalid input.")
    r.table("Table 5.4: Cost of the calculations (Y = simulated years, e = failure events per year)",
            ["Calculation", "Time", "Remark"],
            [["Generate the world", "O(Y · e)", "one random draw per event"],
             ["Single, restart, active-active", "O(Y · e)", "interval union and intersection of sorted lists"],
             ["Active-passive", "O(Y · e log(Y · e))", "sorting of events, a heap of failover timers"],
             ["DR takeover", "O(outages · log DR outages)", "regional events are very rare"],
             ["Markov model", "constant", "a 4 × 4 linear system"]],
            widths=[5.0, 4.4, 5.6], size=10)


def chapter6(r):
    H1(r, "6. RESULTS", 6)
    r.h(2, "6.1  Test results")
    r.para("All 39 automated tests pass (`python -m unittest discover -s tests`, run time a few seconds because several tests simulate tens of thousands of years). Table 6.1 lists them by group.")
    r.table("Table 6.1: Automated tests",
            ["Group", "Tests", "What is checked"],
            [["Availability mathematics", "6", "A = MTBF/(MTBF+MTTR); nines; series, parallel and k-of-n; invalid input; limits of the Markov model; allowed downtime of an SLA"],
             ["Interval arithmetic", "2", "union, intersection, total; failure generator is ordered and inside the horizon"],
             ["Failover state machine", "6", "simple failover; standby fails after the switch; target fails during the switch; both down; original back before the switch ends; outage open at the horizon"],
             ["Disaster recovery", "6", "takeover time; short outage; DR region down at takeover; DR region fails while carrying the service; data-loss means; tiers ordered by speed and cost"],
             ["Simulation against theory", "8", "single VM and active-active against closed forms; active-passive against the Markov model; restart effect; more redundancy never hurts; region floor; same seed same result; unknown strategy"],
             ["Backups", "3", "formula against Monte Carlo; percentile; restore time"],
             ["Planner", "6", "modest target is met cheaply; four nines needs a DR region; RTO limit selects warm standby; tight RPO selects multi-region; impossible target gives no recommendation; a reason for every rejection"],
             ["Interfaces", "2", "command line; HTTP endpoints and the 400 reply"]],
            widths=[3.4, 1.3, 10.3], size=9.5)
    r.h(2, "6.2  The simulation reproduces the mathematics")
    rows = []
    for v in R["validation"]:
        rows.append([v["what"], v["model"], f"{v['exact_unavail']:.3e}", f"{v['sim_unavail']:.3e}", f"{v['error_pct']:+.2f}%"])
    mx = max(abs(v["error_pct"]) for v in R["validation"])
    r.para(f"Table 6.2 compares the simulated unavailability with the exact value for six cases: a single VM and an active-active pair (closed forms, {R['years']:,} simulated years) and four active-passive pairs "
           "(Markov model, 60,000 years, with zone and region failures switched off so that only host failures remain). The largest difference is "
           f"{mx:.1f}%, which is within the sampling error of a simulation of this length, since the downtime of a design that fails rarely is itself a random quantity. The exact models and the simulator are written independently "
           "and agree, which is the main evidence that both are right.")
    r.table("Table 6.2: Simulated unavailability against exact results", ["Case", "Reference", "Exact", "Simulated", "Difference"], rows,
            widths=[6.6, 2.4, 2.0, 2.2, 1.8], size=9)
    r.h(2, "6.3  Six designs on the same failures")
    rows = []
    for k, v in ST.items():
        rows.append([sim.STRATEGIES[k], f"{100 * v['availability']:.4f}%", f"{v['downtime_min_per_year']:.1f}", f"{v['incidents_per_year']:.2f}", f"{v['mean_incident_min']:.0f}", f"{v['longest_incident_min'] / 60:.0f} h"])
    r.para(f"Table 6.3 and Figure 6.1 give the result of {R['years']:,} simulated years with the default parameters of Table 5.2 and the warm-standby DR tier. The vertical bars in the figure show the range over five different random seeds, which "
           "is narrow, so the ranking does not depend on luck.")
    r.table("Table 6.3: Six designs on the same simulated failures", ["Design", "Availability", "Downtime (min/year)", "Incidents per year", "Mean incident (min)", "Longest"], rows,
            widths=[5.2, 2.1, 2.3, 1.9, 2.0, 1.5], size=9)
    r.figure(A + "chart_strategies.png", "Figure 6.1: Downtime per year of the six designs (log scale; bars show the range over five seeds)", width_cm=13.0)
    s = ST
    r.para(f"A single VM is down about {s['single']['downtime_min_per_year'] / 60:.1f} hours a year. **Automatic restart** removes most of the host-repair downtime and brings it to {s['restart']['downtime_min_per_year']:.0f} minutes, "
           f"{100 * (1 - s['restart']['downtime_min_per_year'] / s['single']['downtime_min_per_year']):.0f}% less, for almost no extra cost. A second VM adds little over restart in the same zone ({s['ap-one-zone']['downtime_min_per_year']:.0f} minutes) because the zone and the region are still shared; "
           f"putting the second VM in another zone gives {s['ap-two-zones']['downtime_min_per_year']:.0f} minutes, and active-active across two zones, which needs no failover, {s['aa-two-zones']['downtime_min_per_year']:.0f} minutes. "
           "At that point something changes. The number of incidents per year drops from about 4.9 to 0.07, but the average incident lasts over 30 hours: the remaining downtime is the rare regional disaster, which no arrangement of VMs inside "
           f"one region can survive. A DR region removes it: downtime falls to {s['aa-dr']['downtime_min_per_year']:.1f} minutes a year ({100 * s['aa-dr']['availability']:.4f}%), and the longest incident from {s['aa-two-zones']['longest_incident_min'] / 60:.0f} hours to {s['aa-dr']['longest_incident_min'] / 60:.1f} hours. "
           "This is the main result of the project: past the second nine, availability is bought by protecting against the rare large failure and not by adding more VMs.")
    r.h(2, "6.4  Failover time")
    r.para("Figure 6.2 shows how the downtime of an active-passive pair grows with the failover time, for host failures only (the setting of the Markov model). The downtime is almost proportional to the failover time: "
           f"{FO[0]['host_only_sim_min_per_year']:.1f} minutes a year at one minute, {FO[2]['host_only_sim_min_per_year']:.1f} at five and {FO[-1]['host_only_sim_min_per_year']:.0f} at an hour, because each of the "
           "roughly 4.4 host failures a year costs one failover. The simulation and the Markov model agree up to a failover time of about ten minutes; at 60 minutes the simulation is "
           f"{100 * (FO[-1]['host_only_sim_min_per_year'] / FO[-1]['host_only_markov_min_per_year'] - 1):.0f}% above the model. The difference is expected and is not an error: the model assumes that the failover time is exponentially distributed, with a few very long switches, "
           "while the simulation uses the same fixed time every time, and the two behave differently when the failover is long compared with the repair. For a pair in two zones with all failure types "
           f"(the downtime column of the sweep) the downtime rises from {FO[0]['downtime_min_per_year']:.0f} to {FO[-1]['downtime_min_per_year']:.0f} minutes a year between a one-minute and a one-hour failover, so a failover of an hour is worse than automatic restart ({ST['restart']['downtime_min_per_year']:.0f} minutes).")
    r.figure(A + "chart_failover.png", "Figure 6.2: Downtime from host failures against the failover time (active-passive pair)", width_cm=11.0)
    r.h(2, "6.5  Repair time")
    r.para(f"Figure 6.3 varies the host repair time. For a single VM the downtime grows in proportion to the repair time, from {MT[0]['single']:.0f} minutes a year at one hour to {MT[-1]['single']:,.0f} at 48 hours. "
           f"Automatic restart does not depend on it ({MT[0]['restart']:.0f} to {MT[-1]['restart']:.0f}, because the VM is restarted elsewhere and never waits for the repair). Active-passive and active-active pairs are "
           f"nearly flat while repairs are short, but rise when repairs are slow ({MT[2]['ap-two-zones']:.0f} minutes at 12 hours, {MT[-1]['ap-two-zones']:.0f} at 48 hours) because the second host is more likely to fail while the first is still being repaired. "
           f"At a repair time of 48 hours restart on spare capacity ({MT[-1]['restart']:.0f} minutes) beats a pair of VMs that wait for their hosts to be fixed ({MT[-1]['ap-two-zones']:.0f} minutes). The lesson is that the speed of recovery of a host matters as much as redundancy. The restart result depends on the assumption that spare capacity exists on another host.")
    r.figure(A + "chart_mttr.png", "Figure 6.3: Downtime against the host repair time (log scale)", width_cm=11.5)
    r.h(2, "6.6  Disaster-recovery tiers")
    rows = []
    for t in R["tiers"]:
        rows.append([t["name"], f"{t['rto_min']:g}", f"{t['mean_loss_sim']:.2f}", t["cost_extra"], f"{t['takeovers_per_year']:.3f}", f"{t['downtime_min_per_year']:.1f}"])
    r.para(f"Table 6.4 and Figure 6.4 show the four tiers. A region disaster occurred {TI['warm-standby']['disasters_per_year']:.3f} times a year in the simulation, about once in twenty years, as set by the parameters. "
           "The tiers differ by orders of magnitude in recovery time and data loss, and by a factor of 20 in extra cost. The mean data loss measured in the simulation agrees with the model value of Table 5.3 for every tier "
           "(for backup and restore 730 against 720 minutes). Backup and restore recovers in about four hours and loses half a day of data, which is acceptable only for systems that tolerate both; "
           "pilot light reaches an RTO of about an hour at a small extra cost; warm standby brings it to 20 minutes and about a minute of data loss; multi-region active-active reaches seven minutes (mostly the "
           f"detection time) and a tenth of a minute of data loss at more than twice the cost. The downtime per year shown in the last column is dominated by the disaster takeover itself: {TI['backup-restore']['downtime_min_per_year']:.1f} minutes for backup and restore against "
           f"{TI['multi-active']['downtime_min_per_year']:.1f} for multi-region.")
    r.table("Table 6.4: Disaster-recovery tiers on 20,000 simulated years", ["Tier", "RTO (min)", "Mean data lost (min)", "Extra cost", "Takeovers per year", "Downtime (min/year)"], rows,
            widths=[4.4, 1.8, 2.5, 1.7, 2.4, 2.2], size=9.5)
    r.figure(A + "chart_tiers.png", "Figure 6.4: Recovery time, data loss and cost of the four tiers (the first two on a log scale)", width_cm=14.5)
    r.h(2, "6.7  Backups")
    rows = [[f"{b['interval']:g} min", f"{b['success']:.2f}", f"{b['mean']:.1f}", f"{b['sim_mean']:.1f}", f"{b['p99']:.0f}"] for b in R["backup"]]
    r.para("Table 6.5 gives the average age of the newest good backup for different schedules, together with the Monte Carlo check of the formula (100,000 trials each, always within 0.4% of the formula). "
           "An unreliable backup job is a hidden risk: a daily backup that succeeds 98% of the time has a mean data age of 749 minutes and a 1-in-100 worst case of three days, while the same schedule with a perfect job gives 720 minutes and one day. "
           "Moving from daily to hourly backups divides the data loss by 24 (Figure 6.5). The restore time depends on the data size: at 100 MB/s it takes about "
           + ", ".join(f"{x['minutes'] / 60:.1f} hours for {x['size_gb'] / 1000:g} TB" if x["size_gb"] >= 1000 else f"{x['minutes']:.0f} minutes for {x['size_gb']} GB" for x in R["restore"]) +
           ", so a 4-hour RTO for backup and restore is realistic only up to roughly a terabyte of data.")
    r.table("Table 6.5: Age of the newest good backup", ["Interval", "Success rate", "Mean age (formula, min)", "Mean age (simulated, min)", "99th percentile (min)"], rows,
            widths=[2.4, 2.4, 3.6, 3.6, 3.0], size=10)
    r.figure(A + "chart_backup.png", "Figure 6.5: Average data age against the backup interval", width_cm=10.5)
    r.h(2, "6.8  The planner")
    rows = []
    for name, v in PL.items():
        rows.append([name, f"{100 * v['target']:.3f}%", "-" if v["rto"] is None else f"{v['rto']} min", "-" if v["rpo"] is None else f"{v['rpo']} min", (v["choice"] or "none").replace("aa-dr + ", "active-active + DR: "), "-" if v["cost"] is None else v["cost"]])
    r.para("Table 6.6 shows the planner on four typical requirements. An internal tool that needs 99.9% and has no recovery limits is served by automatic restart at a cost of 1.1 VMs. A web shop that needs four nines, an RTO of an hour and an RPO of 15 minutes needs a DR region, and the cheapest tier whose "
           "recovery time is within an hour is warm standby: pilot light fails because its recovery time of 65 minutes is five minutes above the limit, and backup and restore fails both limits. A payment service with an RTO of 15 minutes and an RPO of one minute "
           "can only be served by multi-region active-active at 4.2 VMs, and it is also the choice when the target is raised to five nines with the same limits. Figure 6.6 shows the options of the web-shop case: cost rises with every step, and only the DR designs pass the four-nines line.")
    r.table("Table 6.6: Planner results", ["Case", "Availability target", "RTO limit", "RPO limit", "Recommended design", "Cost"], rows, widths=[2.6, 2.4, 1.8, 1.8, 5.4, 1.2], size=9.5)
    r.figure(A + "chart_cost.png", "Figure 6.6: Cost against availability for the web-shop case (green: meets all limits)", width_cm=12.0)
    r.h(2, "6.9  Browser interface")
    r.para("Figures 6.7 to 6.10 show the four tabs of the browser interface (`python -m vmdr.server`).")
    r.figure(A + "shot_avail.png", "Figure 6.7: Availability tab: one host, redundant copies and the downtime allowed by common targets", width_cm=11.5)
    r.para("In Figure 6.7 a host with MTBF 2,000 h and MTTR 4 h has 99.8004% availability, 2.70 nines and 17.5 hours of downtime a year. Two independent copies reach 99.9996% (5.4 nines) and three about 8 nines; the second table lists what the usual targets allow, for example 52.6 minutes a year for 99.99%.")
    r.figure(A + "shot_compare.png", "Figure 6.8: Compare tab: six designs simulated over 2,000 years with the warm-standby tier", width_cm=11.5)
    r.para("Figure 6.8 runs the six designs for 2,000 years with editable failure parameters and a choice of DR tier. The bars show the downtime, and the text under the table reports how often a region disaster occurs, the recovery time and the mean data lost.")
    r.figure(A + "shot_plan.png", "Figure 6.9: Planner tab: targets of 99.99%, RTO 60 minutes and RPO 15 minutes", width_cm=11.5)
    r.para("In Figure 6.9 the planner lists every option with its cost, availability, recovery time and data loss. The grey rows fail, each with its reasons; the two rows in normal colour meet all limits, and the highlighted row, warm standby at a cost of 3.10, is the cheapest of them.")
    r.figure(A + "shot_backup.png", "Figure 6.10: Backups tab: data age and restore time", width_cm=11.0)
    r.para("Figure 6.10 shows a daily backup that succeeds 98% of the time: the average age of the newest good backup is 12.5 hours, one time in 100 it is 3.0 days old, and restoring 500 GB at 100 MB/s takes 115 minutes.")
    r.h(2, "6.10  Performance")
    r.para(f"Twenty thousand simulated years for all six designs take {R['time_compare_s']:.1f} seconds, and the planner, which evaluates nine options on 4,000 years, answers in {R['time_plan_s']:.1f} seconds, which is quick enough for the browser interface. "
           "The times were measured on one machine and one Python version and show the order of magnitude only.")
    r.h(2, "6.11  Discussion")
    r.para("The results support the aims of the project. The simulator agrees with exact mathematics in every case where an exact answer exists, so the numbers for the cases without one can be trusted to the same degree. "
           "Three findings stand out. First, the downtime of a design is shaped by its weakest rare event: below roughly 99.97% availability the figure is set by region disasters, and only a DR region lowers it. Second, "
           "the quality of recovery matters as much as redundancy: a slow failover or a slow repair can make a pair of VMs worse than a single VM that restarts quickly on spare capacity. Third, the DR tier is a trade-off with no free option: "
           "each step cuts the recovery time and data loss by a large factor and raises the cost, and the planner's job is to find the cheapest step that still meets the limits.")
    r.para("The limits of the evidence should be stated just as clearly. The failure rates, the repair times and the tier parameters are assumptions of the model and not measurements of a cloud provider, "
           "so the absolute figures (21 hours, 3.7 minutes) would change with real data, and only the relationships between the designs carry over. The model treats failures as independent apart from the zone and region hierarchy, and uses exponential "
           "times; real outages are often correlated and heavy-tailed, and software and operator faults, which Gray [5] found to be a leading cause of failures, hit all copies at once, so redundancy would help less than here.")


def chapter7(r):
    H1(r, "7. CONCLUSION", 7)
    r.para("This mini project built a tool for the availability and disaster recovery of virtual machines. It combines the closed-form mathematics of availability and an exact Markov model of an active-passive pair with a Monte Carlo simulator "
           "that fails hosts, zones and regions at random, judges six deployment designs on the same failures, models four disaster-recovery tiers and calculates backups and restores. A planner uses the models to recommend the "
           "cheapest design that meets an availability target and RTO and RPO limits, and to explain why the others do not. The simulator reproduces the exact results within 2.4% in six comparisons, and 39 automated tests pass.")
    r.para(f"The experiments give three practical messages. A single VM was down {ST['single']['downtime_min_per_year'] / 60:.0f} hours a year; automatic restart on spare capacity removes about {100 * (1 - ST['restart']['downtime_min_per_year'] / ST['single']['downtime_min_per_year']):.0f}% of that at almost no extra cost; "
           f"and beyond the second VM the downtime that remains is the rare regional disaster ({ST['aa-two-zones']['downtime_min_per_year'] / 60:.1f} hours a year), which only a DR region can remove ({ST['aa-dr']['downtime_min_per_year']:.1f} minutes with warm standby). "
           "The speed of failover and repair matters as much as the number of copies. And the DR tier is chosen by the RTO and RPO that the business needs: warm standby for an hour and 15 minutes, multi-region for minutes and seconds, at a cost that grows with each step.")
    r.h(2, "7.1  Limitations")
    r.bullets(["The model uses assumed failure rates, repair times, tier parameters and costs; it is not calibrated on a real cloud provider.",
               "Failures are independent except through the zone and region hierarchy, and times are exponential; correlated and heavy-tailed outages are not modelled.",
               "Software faults, network partitions, capacity shortages and human error, which cause many real outages, are outside the model.",
               "Auto-restart assumes spare capacity on another host; the load balancer is assumed to react at once.",
               "A region disaster is modelled as an outage; data destruction and ransomware are treated only through backups.",
               "The costs are relative VM equivalents, not prices."])
    r.h(2, "7.2  Future scope")
    r.bullets(["Calibrate the model with real incident data and published provider figures, and add confidence intervals to the simulated results.",
               "Model correlated failures (common power, common software release) and heavy-tailed repair times.",
               "Add capacity planning for auto-restart, so that the spare capacity it needs is part of the cost.",
               "Add more topologies: three zones, k-out-of-n clusters behind a load balancer, and multi-region active-active with traffic splitting.",
               "Connect the planner to a cloud provider's price list and to the configuration of a real deployment, so that recommendations come with a monthly cost.",
               "Add a failover drill simulator that estimates the RTO of a procedure from the time taken by each step.",
               "Include the time to detect failures, and the effect of false alarms, in the failover model."])


def chapter8(r):
    H1(r, "8. REFERENCE", 8)
    refs = [
        "K. S. Trivedi, Probability and Statistics with Reliability, Queuing, and Computer Science Applications, 2nd ed. New York, NY: Wiley, 2002.",
        "A. Birolini, Reliability Engineering: Theory and Practice, 8th ed. Berlin: Springer, 2017.",
        "A. M. Law, Simulation Modeling and Analysis, 5th ed. New York, NY: McGraw-Hill, 2015.",
        "L. A. Barroso, J. Clidaras and U. Hölzle, The Datacenter as a Computer: Designing Warehouse-Scale Machines, 3rd ed. San Rafael, CA: Morgan & Claypool, 2018.",
        "J. Gray, \"Why do computers stop and what can be done about it?\" Tandem Computers, Technical Report 85.7, 1985.",
        "P. Barham et al., \"Xen and the art of virtualization,\" in Proceedings of the 19th ACM Symposium on Operating Systems Principles (SOSP), 2003, pp. 164–177.",
        "C. Clark et al., \"Live migration of virtual machines,\" in Proceedings of the 2nd USENIX Symposium on Networked Systems Design and Implementation (NSDI), 2005, pp. 273–286.",
        "B. Cully et al., \"Remus: High availability via asynchronous virtual machine replication,\" in Proceedings of the 5th USENIX Symposium on Networked Systems Design and Implementation (NSDI), 2008, pp. 161–174.",
        "Amazon Web Services, \"Disaster Recovery of Workloads on AWS: Recovery in the Cloud,\" AWS Whitepaper (backup and restore, pilot light, warm standby and multi-site active-active). [Online]. Available: https://docs.aws.amazon.com/",
        "Microsoft, \"Service Level Agreements (SLA) for Online Services\" and \"Azure Well-Architected Framework: Reliability,\" Microsoft documentation. [Online]. Available: https://learn.microsoft.com/azure/",
        "G. Bolch, S. Greiner, H. de Meer and K. S. Trivedi, Queueing Networks and Markov Chains: Modeling and Performance Evaluation with Computer Science Applications, 2nd ed. Hoboken, NJ: Wiley, 2006.",
    ]
    for i, t in enumerate(refs, 1):
        p = r.para(f"[{i}]  {t}", size=12, spacing=1.15, after=5, indent=1.0)
        p.paragraph_format.first_line_indent = r.cm(-1.0)
