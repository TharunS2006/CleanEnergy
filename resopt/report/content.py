"""Chapters of the CPU, Memory and I/O Resource Optimization report. Every measured number is read from bench_results.json."""
import json, pathlib, sys
HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
R = json.load(open(ROOT / "bench_results.json"))
A = "assets/"
CPU = R["cpu"]["mixed"]; SHORT = R["cpu"]["short"]; MEM = R["memory"]; DSK = R["disk"]; SC = R["scenario"]; Q = {r["quantum"]: r for r in R["quantum"]}
from resopt import cpu, memory, disk, optimizer
from resopt.cpu import Proc


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


def chapter1(r):
    H1(r, "1. INTRODUCTION", 1)
    r.h(2, "1.1  Background")
    r.para("A computer runs many programs at once on a small number of physical resources. The operating system is the "
           "program that shares those resources, and three of them decide most of what a user experiences: the processor (CPU), "
           "the main memory and the input/output devices, of which the disk is the slowest and the most important. For each "
           "resource the operating system has to take a decision again and again. The CPU scheduler decides which ready process "
           "runs next. The virtual-memory manager decides which page to remove from memory when a new page must be loaded. The disk "
           "scheduler decides which of the waiting requests the disk arm should serve first. The textbooks of Silberschatz, Galvin and Gagne [1], "
           "Tanenbaum and Bos [2] and Stallings [3] describe a family of algorithms for each decision.")
    r.para("The algorithms have different strengths. Shortest-job-first scheduling gives the lowest average waiting time but needs to know how long "
           "a job will run, and it can starve long jobs. Round robin gives every process a quick first response but pays for it in context "
           "switches. LRU page replacement works well when programs reuse recent pages, and FIFO can behave in the surprising way known as Belady's "
           "anomaly [5], where giving a program more memory makes it fault more often. Shortest-seek-time-first disk scheduling moves the arm the "
           "least, yet requests far from the head can wait for a long time. None of these algorithms is best in every situation, so "
           "*optimising* the use of a resource means choosing the algorithm, and tuning its parameters, for the workload at hand.")
    r.table("Table 1.1: The three resources, the decision taken for each and the algorithms studied",
            ["Resource", "Decision made by the operating system", "Algorithms in this project", "Main measure"],
            [["CPU", "Which ready process runs next, and for how long", "FCFS, SJF, SRTF, PRIORITY, PRIORITY-P, RR", "Waiting, turnaround and response time; context switches"],
             ["Memory", "Which page to replace when all frames are full", "FIFO, LRU, OPT, CLOCK", "Number of page faults"],
             ["I/O (disk)", "Which pending request the disk arm serves next", "FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK", "Total head movement in cylinders"]],
            widths=[2.0, 5.0, 4.8, 3.2], size=10)
    r.h(2, "1.2  Problem Statement")
    r.para("In a course the algorithms are met one by one, each on a single example that has been chosen so that its answer is a "
           "round number. A student can follow the example, but cannot easily answer the questions that matter in practice: how do the "
           "algorithms compare on a workload I choose? How much better is the best one than the simplest one? When does "
           "the ranking change? What is a good value for the time quantum, or for the number of frames? Existing tools tend to cover only one "
           "resource, to show only one algorithm at a time, or to stop at drawing a chart without saying which algorithm should be used.")
    r.para("The problem addressed here is to build one tool that simulates the main algorithms for the CPU, the memory and the disk, "
           "runs them side by side on the same workload, measures them with the standard metrics, and recommends the best choice with a "
           "reason, while reproducing the textbook results exactly so that its answers can be trusted.")
    r.h(2, "1.3  Motivation")
    r.para("Three observations motivated the project. First, the gap between a simple policy and a good one is large and easy "
           "to measure: on the same process set the average waiting time can differ by a factor of five between FCFS and SJF "
           "(Section 6.2). Second, several classical results are properties that can be tested rather than only proved, such as "
           "the optimality of SRTF for waiting time, the absence of Belady's anomaly in LRU and OPT, and the fact that OPT is a lower bound "
           "for every replacement rule. A simulator allows each of them to be checked on thousands of generated workloads. Third, "
           "parameters such as the round-robin quantum have no universal best value; the right value depends on the lengths of the jobs, and "
           "a tool that sweeps the parameter makes that visible.")
    r.h(2, "1.4  Scope")
    r.para("The tool is a simulator, not a modification of a real kernel. Time is counted in whole units. The CPU model has one "
           "processor, processes whose bursts are known in advance, and no I/O inside a process; context switches are counted but cost no time unless "
           "a cost is given to the tuning function. The memory model is one reference string running against a fixed number of "
           "frames. The disk model is a single arm on a disk of a given number of cylinders, with all requests present at the start; seek time is taken "
           "to be proportional to the distance moved and rotational delay is ignored. Multilevel feedback queues, multiple processors, "
           "working-set page allocation among several processes, and disk request arrival over time are outside the scope and are listed in Section 7.2.")


def chapter2(r):
    H1(r, "2. OBJECTIVES", 2)
    r.para("The main objective is to design and implement a simulator and optimizer for the CPU, memory and I/O resources of an "
           "operating system, and to evaluate the classical algorithms on generated workloads. The specific objectives are:")
    r.bullets(["To simulate six CPU scheduling algorithms and report waiting, turnaround and response time, utilisation, throughput and context switches.",
               "To simulate four page-replacement algorithms and report page faults, hits and fault rate, including the frame contents after every reference.",
               "To simulate six disk-scheduling algorithms and report the path of the arm and the total head movement.",
               "To provide an optimizer that compares the algorithms on the same workload, picks the best, explains the choice and states the saving against the simplest policy.",
               "To tune the two main parameters, the round-robin time quantum and the number of frames.",
               "To verify the simulators against the worked examples of the textbooks and against theoretical properties, using automated tests.",
               "To offer a command-line interface and a browser interface with Gantt charts, frame tables and head-path plots."])
    r.table("Table 2.1: Functional requirements",
            ["ID", "Requirement"],
            [["FR1", "Simulate CPU scheduling with FCFS, SJF, SRTF, PRIORITY, PRIORITY-P and RR for a list of processes with arrival time, burst and priority"],
             ["FR2", "Simulate page replacement with FIFO, LRU, OPT and CLOCK for a reference string and a number of frames"],
             ["FR3", "Simulate disk scheduling with FCFS, SSTF, SCAN, C-SCAN, LOOK and C-LOOK for a request queue, head position and direction"],
             ["FR4", "Compare all algorithms of a resource on one workload and recommend the best with a reason"],
             ["FR5", "Show a Gantt chart, the frame table after each reference and the path of the head"],
             ["FR6", "Sweep the time quantum and the number of frames and report the best value"],
             ["FR7", "Report the combined saving of the recommended choices in one scenario"],
             ["FR8", "Reject wrong input (empty workload, zero burst, request outside the disk) with a clear message"]],
            widths=[1.6, 13.4], size=10.5)
    r.table("Table 2.2: Non-functional requirements",
            ["Requirement", "How it is met"],
            [["Correctness", "Textbook examples reproduced exactly; theoretical properties checked on generated workloads"],
             ["Repeatability", "Every generated workload comes from a fixed random seed"],
             ["Portability", "Python standard library only; nothing to install"],
             ["Speed", "A workload of 200 processes is compared across all six algorithms in a fraction of a second"],
             ["Clarity", "Each algorithm is a short function that follows its textbook definition"]],
            widths=[3.6, 11.4], size=10.5)


def chapter3(r):
    H1(r, "3. TOOLS AND TECHNOLOGIES", 3)
    r.para("The whole project is written in Python so that every algorithm reads like its description in the textbook, "
           "and it uses no third-party package. Table 3.1 lists what was used.")
    r.table("Table 3.1: Tools and technologies used",
            ["Item", "Tool", "Purpose"],
            [["Language", "Python 3.10 or newer (developed and tested on 3.13)", "Simulators, optimizer, interfaces"],
             ["Libraries", "Standard library only: `dataclasses`, `random`, `http.server`, `json`, `unittest`", "Seeded generators, server, tests"],
             ["Browser interface", "One HTML file with CSS and plain JavaScript", "Three tabs, tables, Gantt chart, frame table, head path in SVG"],
             ["Server", "`http.server.ThreadingHTTPServer`", "JSON endpoints used by the page"],
             ["Testing", "`unittest`", "29 automated tests"],
             ["Charts for this report", "matplotlib", "Figures 6.1 to 6.7 (not needed to run the tool)"],
             ["Editor and shell", "Visual Studio Code, PowerShell or any terminal", "Development"]],
            widths=[3.0, 6.0, 6.0], size=10)
    r.h(2, "3.1  Running the project")
    r.para("The project is a folder named `resopt`. No installation step is needed. From inside the folder:")
    r.code("""
python -m unittest discover -s tests      # the 29 automated tests
python -m resopt.cli demo                 # textbook examples, all three resources
python -m resopt.cli cpu --procs P1:0:24,P2:0:3,P3:0:3 --quantum 4
python -m resopt.cli memory --refs 7,0,1,2,0,3,0,4,2,3,0,3,2,1,2,0,1,7,0,1 --frames 3
python -m resopt.cli disk --requests 98,183,37,122,14,124,65,67 --head 53
python -m resopt.server 8000              # browser interface at http://127.0.0.1:8000
python bench.py                           # the experiments of Chapter 6
""")


def chapter4(r):
    H1(r, "4. ARCHITECTURE DIAGRAM", 4)
    r.para("The tool has four layers (Figure 4.1). The presentation layer is the command line, the browser page and the small HTTP "
           "server behind the page. The optimizer layer compares algorithms, tunes parameters and combines the three resources. "
           "The simulators are three independent modules, one per resource, and each has the same shape: a function that takes a "
           "workload and the name of an algorithm and returns a result with the full trace and the metrics. At the bottom, the "
           "workload generators produce seeded random inputs. A layer calls only the layer below it, so the simulators can be tested "
           "without any interface.")
    r.figure("diagrams/fig41.png", "Figure 4.1: Layers of the Resource Optimization tool", width_cm=14.0)
    r.table("Table 4.1: Module responsibilities",
            ["File", "Lines", "Responsibility"],
            [["`resopt/cpu.py`", loc("resopt/cpu.py"), "Six CPU scheduling algorithms, metrics, Gantt chart"],
             ["`resopt/memory.py`", loc("resopt/memory.py"), "FIFO, LRU, OPT and CLOCK page replacement with a step-by-step trace"],
             ["`resopt/disk.py`", loc("resopt/disk.py"), "Six disk-arm scheduling algorithms and head path"],
             ["`resopt/optimizer.py`", loc("resopt/optimizer.py"), "Ranking, recommendation, quantum and frame tuning, combined scenario"],
             ["`resopt/workloads.py`", loc("resopt/workloads.py"), "Seeded generators of processes, reference strings and disk requests"],
             ["`resopt/cli.py`, `resopt/server.py`", loc("resopt/cli.py") + loc("resopt/server.py"), "Command line and HTTP server"],
             ["`web/index.html`", loc("web/index.html"), "Browser page"],
             ["`tests/test_resopt.py`", loc("tests/test_resopt.py"), "29 automated tests"],
             ["`bench.py`", loc("bench.py"), "Experiments of Chapter 6"]],
            widths=[5.4, 1.5, 8.1], size=10)
    r.h(2, "4.1  From a workload to a recommendation")
    r.para("Figure 4.2 shows what happens for one request. The workload is passed to every algorithm of the resource it belongs to, so the "
           "comparison is always like for like. Each simulator returns the metrics of its algorithm. The optimizer ranks them by the "
           "relevant metric (average waiting time for the CPU, page faults for memory, head movement for the disk), picks the best, and "
           "compares it with the baseline: FCFS for the CPU, FIFO for memory and FCFS for the disk. The result is the recommendation, the "
           "percentage saved, and a sentence that explains why the algorithm wins and what its drawback is. For memory the recommendation "
           "never names OPT, because OPT needs to know the future and is shown only as the lower bound that no real rule can beat.")
    r.figure("diagrams/fig42.png", "Figure 4.2: From a workload to a recommendation", width_cm=14.0)


def chapter5(r):
    H1(r, "5. METHODOLOGY", 5)
    r.h(2, "5.1  Overall approach")
    r.para("The method has three parts. First, each algorithm is implemented as a simulator that follows its textbook definition and returns "
           "a complete trace, so that any result can be checked by hand. Second, the simulators are validated against known answers "
           "and against theoretical properties. Third, the simulators are run on seeded random workloads to measure how the algorithms "
           "compare, and the optimizer turns those comparisons into recommendations. Every random workload comes from a numbered seed, "
           "so every number in Chapter 6 can be reproduced by running `bench.py`.")
    r.h(2, "5.2  CPU scheduling")
    r.para("A process has an arrival time, a CPU burst and, for priority scheduling, a priority in which a smaller number means more urgent. "
           "Time advances in whole units. For every process the simulator records the time of its first run and of its completion, and from them the "
           "standard measures: **turnaround time** = completion − arrival; **waiting time** = turnaround − burst; **response time** = first run − arrival. "
           "The system measures are **utilisation** (busy time divided by the time from the first arrival to the last completion), **throughput** "
           "(processes completed per time unit) and the number of **context switches**, counted whenever the processor passes from one process to a different one.")
    r.table("Table 5.1: CPU scheduling algorithms",
            ["Algorithm", "Process chosen", "Pre-emptive", "Strength", "Weakness"],
            [["FCFS", "earliest arrival", "no", "simple, fair by arrival", "convoy effect: short jobs wait behind a long one"],
             ["SJF", "shortest burst", "no", "low average waiting", "needs the burst in advance; starves long jobs"],
             ["SRTF", "shortest remaining time", "yes", "minimum average waiting time", "starves long jobs; more switches"],
             ["PRIORITY", "smallest priority number", "no", "respects importance", "low-priority starvation; ignores length"],
             ["PRIORITY-P", "smallest priority number, at once", "yes", "urgent work starts immediately", "same starvation risk"],
             ["RR", "queue order, one quantum at a time", "yes", "quick first response, fair", "many switches; waiting grows with the quantum"]],
            widths=[2.3, 3.4, 1.8, 3.6, 3.9], size=9.5)
    r.para("Ties are broken by arrival time and then by the order in which processes were entered, and a running process is kept when "
           "it ties with a newcomer, which avoids context switches that would change nothing. The non-pre-emptive algorithms run a process to "
           "the end of its burst. The pre-emptive algorithms re-decide at every time unit. Round robin keeps a queue: a process "
           "runs for at most one quantum, processes that arrive during that time join the queue before the interrupted process is put at its end (the "
           "convention of the textbooks), and when the queue is empty the processor idles until the next arrival. Idle periods appear in the Gantt chart "
           "and lower the utilisation.")
    r.para("For average waiting time SRTF is not merely good but provably optimal among all scheduling disciplines that do not idle "
           "while work is waiting [6]. The argument is an exchange: if a process with more remaining work is ever run while a shorter one is waiting, "
           "swapping them cannot increase the sum of the completion times. This gives a property that is easy to test: no other algorithm "
           "may beat SRTF on any workload (Section 5.7).")
    r.h(2, "5.3  Page replacement")
    r.para("A reference string is the sequence of pages that a program touches. Memory has a fixed number of frames. A reference to a page "
           "that is already in a frame is a hit; otherwise a page fault occurs, and if all frames are full a victim must be chosen. "
           "The four rules are: **FIFO** removes the page that has been in memory longest. **LRU** removes the page that has not been used for "
           "the longest time, which uses the recent past to predict the near future. **OPT** removes the page whose next use is farthest away, "
           "which gives the fewest possible faults for the string [10] but cannot be used in a real system because it needs the future; it serves here as "
           "a lower bound. **CLOCK** (second chance) [4] arranges the frames in a circle with a reference bit per page and a hand: the hand skips pages "
           "whose bit is set, clearing the bit as it passes, and replaces the first page whose bit is clear, so a page that was used again gets a "
           "second chance. CLOCK approximates LRU at a much lower cost.")
    r.para("Two classical properties are tested. A replacement rule is a **stack algorithm** if the set of pages in memory with *n* frames is always "
           "contained in the set with *n* + 1 frames; LRU and OPT are stack algorithms [8], so adding a frame can never add faults. FIFO is not, and it can "
           "suffer **Belady's anomaly** [5]: on the string 1 2 3 4 1 2 5 1 2 3 4 5 it makes 9 faults with three frames and 10 with four.")
    r.h(2, "5.4  Disk scheduling")
    r.para("The disk has a number of cylinders (200 in the experiments), the head is on one of them, and a list of cylinder numbers is waiting. "
           "**FCFS** serves them in arrival order. **SSTF** always serves the nearest request. **SCAN** [7], the elevator algorithm, sweeps in one direction "
           "to the end of the disk, serving requests on the way, then reverses. **C-SCAN** sweeps in one direction only: at the end it returns to the "
           "other end and sweeps again, which gives more uniform waiting. **LOOK** and **C-LOOK** are the versions of SCAN and C-SCAN that turn "
           "round at the last request instead of at the end of the disk. The total head movement is the sum of the distances travelled; the return trip "
           "of C-SCAN and C-LOOK is counted because the arm really moves that distance. Table 5.2 gives the totals for the textbook queue "
           "98, 183, 37, 122, 14, 124, 65, 67 with the head at cylinder 53, which can be checked by hand.")
    q = [98, 183, 37, 122, 14, 124, 65, 67]
    rows = [[a, disk.simulate(a, q, 53, 200, 1)["total"], disk.simulate(a, q, 53, 200, -1)["total"]] for a in disk.ALGORITHMS]
    r.table("Table 5.2: Head movement for the textbook queue (head at 53, 200 cylinders)", ["Algorithm", "Moving up first", "Moving down first"], rows,
            widths=[4.0, 4.5, 4.5], size=10.5)
    r.h(2, "5.5  The optimizer")
    r.para("The optimizer is deliberately simple, so that its decisions can be explained. For each resource it runs all algorithms on the "
           "same workload and ranks them by one metric: average waiting time for the CPU, number of page faults for memory (OPT excluded from the "
           "choice), and total head movement for the disk. Ties are broken by the order of the algorithm list. The saving is the "
           "percentage by which the best result is lower than the baseline, and a short explanation of the winner, with its known drawback, is attached to "
           "the answer. The other metrics are always reported as well, because the best algorithm for waiting time is not always the best for "
           "response time or fairness.")
    r.para("**Quantum tuning.** For round robin the optimizer sweeps the quantum and scores each value with *average turnaround + c × context switches ÷ n*, "
           "where *n* is the number of processes and *c* is the time lost at each context switch. The value of *c* is a parameter of the model (0.5 time units in "
           "the experiments), not a measurement. A small quantum gives a fast response but many switches; a large quantum approaches FCFS. **Frame tuning.** "
           "For memory the optimizer computes the fault rate for 1, 2, 3, ... frames and reports the smallest number that reaches a target rate. **Combined scenario.** "
           "The function `optimise()` takes one workload for each resource, applies the three recommendations and reports the saving of each against its baseline.")
    r.h(2, "5.6  Workload generation")
    r.table("Table 5.3: Generators of workloads (all seeded)",
            ["Workload", "Parameters"],
            [["Processes (mixed)", "8 processes; arrival uniform from 0 to 30; 70 % short bursts (1 to 5) and 30 % long bursts (10 to 30); priority 1 to 5"],
             ["Processes (short)", "same, with every burst between 1 and 6"],
             ["Page references (locality)", "200 references over 20 pages; the program works in a set of 5 pages for 40 references (90 % of references fall in the set, 10 % anywhere), then moves to a new set"],
             ["Page references (uniform)", "200 references, every one of 20 pages equally likely: no locality at all"],
             ["Disk requests (uniform)", "20 requests on 200 cylinders, head at a random cylinder"],
             ["Disk requests (clustered)", "20 requests around three busy regions (normal distribution, standard deviation 8 cylinders)"]],
            widths=[4.2, 10.8], size=10)
    r.para("The mixed process workload imitates a system with many short interactive jobs and a few long computations. The locality "
           "reference string imitates the way real programs reuse a working set of pages for a while and then change phase [9]. The uniform string is the worst case "
           "for any rule that tries to predict the future from the past.")
    r.h(2, "5.7  Testing methodology")
    r.para("The 29 tests are of four kinds. **Textbook cross-checks** reproduce the worked examples of [1]: average waiting 17, 3 and 5.67 for FCFS, SJF and round "
           "robin; 15, 12 and 9 faults for FIFO, LRU and OPT; the totals of Table 5.2. **Hand-checked small cases** test pre-emption (SRTF and PRIORITY-P interrupt a running process, SJF does not), idle gaps, "
           "the second chance of CLOCK and the frame table. **Property tests** run on generated workloads: SRTF is never beaten on average waiting time (150 workloads); "
           "the faults of LRU and OPT never increase when frames are added (60 strings); OPT is never beaten by any rule (40 strings); LOOK never moves more than SCAN "
           "(50 queues); every request is visited by every disk algorithm; and for every process of every algorithm waiting = turnaround − burst, "
           "while the total busy time equals the total of the bursts (360 simulations). **Interface tests** call the command line and the three HTTP endpoints "
           "and check that bad input returns an error instead of a wrong answer.")
    r.table("Table 5.4: Cost of the simulations (n = processes or references, F = frames, T = total CPU time, R = requests)",
            ["Simulator", "Time", "Remark"],
            [["CPU, non-pre-emptive and pre-emptive", "O(T · n)", "one decision per time unit for the pre-emptive algorithms"],
             ["CPU, round robin", "O(n + T / q)", "one decision per quantum"],
             ["Page replacement, FIFO, LRU, CLOCK", "O(n · F)", "scan of the frames at a fault"],
             ["Page replacement, OPT", "O(n² · F) worst case", "looks forward in the string for every candidate"],
             ["Disk, SSTF", "O(R²)", "the nearest request is searched again at every step"],
             ["Disk, the others", "O(R log R)", "sorting the requests"]],
            widths=[5.4, 3.6, 6.0], size=10)


def chapter6(r):
    H1(r, "6. RESULTS", 6)
    r.h(2, "6.1  Test results")
    r.para("All 29 automated tests pass (`python -m unittest discover -s tests`, run time under one second). Table 6.1 lists them by group.")
    r.table("Table 6.1: Automated tests",
            ["Group", "Tests", "What is checked"],
            [["CPU scheduling", "9", "textbook waiting times; round-robin Gantt chart; SRTF pre-empts and SJF does not; priority order; pre-emptive priority; idle gap and utilisation; time accounting on 360 simulations; SRTF never beaten on 150 workloads; bad input"],
             ["Page replacement", "7", "15, 12, 9 faults; Belady's anomaly for FIFO and not for LRU; no anomaly for LRU and OPT on 60 strings; OPT lower bound on 40 strings; only cold faults with enough frames; CLOCK second chance; frame table"],
             ["Disk scheduling", "5", "totals in both directions; every request visited; LOOK never above SCAN on 50 queues; bad input"],
             ["Optimizer", "6", "CPU, memory and disk recommendations; quantum sweep; frames needed; combined scenario has no negative saving"],
             ["Interfaces", "2", "command line; HTTP endpoints, including the 400 reply for a request outside the disk"]],
            widths=[3.0, 1.4, 10.6], size=10)
    r.h(2, "6.2  Textbook examples reproduced")
    r.para("The first check of a simulator is that it gives the answers printed in the textbook. Three processes arrive at time 0 with bursts of 24, 3 and 3. "
           "Figure 6.1 shows the Gantt charts. FCFS runs the long process first, so the two short ones wait 24 and 27 units and the average waiting time is 17. "
           "SJF runs the short ones first and the average falls to 3, which is 82% lower. Round robin with a quantum of 4 gives 5.67 (6, 4 and 7 units). These are "
           "the numbers of [1]. For page replacement the reference string 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 with three frames gives 15 faults for FIFO, 12 for LRU "
           f"and 9 for OPT, and {memory.simulate('CLOCK', [7,0,1,2,0,3,0,4,2,3,0,3,2,1,2,0,1,7,0,1], 3)['faults']} for CLOCK. Figure 6.2 shows how the arm moves for four disk algorithms on the queue of Table 5.2.")
    r.figure(A + "chart_gantt.png", "Figure 6.1: Gantt charts of FCFS, SJF and round robin for the textbook example", width_cm=13.5)
    r.figure(A + "chart_diskpath.png", "Figure 6.2: Head movement for the textbook queue (head at 53, moving up first); the total is in each title", width_cm=14.5)
    r.h(2, "6.3  CPU scheduling on 500 generated workloads")
    r.para("Table 6.2 gives the average of each measure over 500 mixed workloads of eight processes (quantum 4), and Figure 6.3 shows the waiting and response "
           "times. The last column is the share of the workloads in which the algorithm reached the lowest average waiting time (ties count for every algorithm involved).")
    rows = [[a, v["avg_waiting"], v["avg_turnaround"], v["avg_response"], v["max_waiting"], v["switches"], f'{v["best_share"]:.1f}%'] for a, v in CPU.items()]
    r.table("Table 6.2: CPU scheduling, mean of 500 mixed workloads", ["Algorithm", "Avg waiting", "Avg turnaround", "Avg response", "Max waiting", "Switches", "Best"], rows,
            widths=[2.6, 2.1, 2.5, 2.2, 2.1, 1.8, 1.7], size=9.5)
    r.figure(A + "chart_cpu.png", "Figure 6.3: Average waiting and response time of the six algorithms", width_cm=12.5)
    r.para(f"SRTF has the lowest average waiting time ({CPU['SRTF']['avg_waiting']}) and was best or tied-best in {CPU['SRTF']['best_share']:.0f}% of the workloads, as the theory predicts; it is "
           f"{100 * (CPU['FCFS']['avg_waiting'] - CPU['SRTF']['avg_waiting']) / CPU['FCFS']['avg_waiting']:.0f}% lower than FCFS ({CPU['FCFS']['avg_waiting']}). "
           f"Non-pre-emptive SJF reaches {CPU['SJF']['avg_waiting']}, so about two thirds of SRTF's gain over FCFS comes from simply choosing the short job, and the rest from pre-empting. "
           f"Priority scheduling gives no gain here ({CPU['PRIORITY']['avg_waiting']} and {CPU['PRIORITY-P']['avg_waiting']}) because the priorities in the generator are random and unrelated to the length "
           f"of the jobs. Round robin has the best response time ({CPU['RR']['avg_response']}, against {CPU['SRTF']['avg_response']} for SRTF) but needs {CPU['RR']['switches']} context switches per workload, about twice as many as the "
           f"others, and its average waiting time ({CPU['RR']['avg_waiting']}) is much worse than SRTF's.")
    r.para(f"Two further observations are worth recording. **Utilisation is the same for all six algorithms** ({CPU['FCFS']['utilisation']:.3f}) because every one of them keeps the processor busy whenever work is "
           "waiting; the idle time comes only from gaps between arrivals. A scheduler cannot raise utilisation, it can only choose whose work is done first, so the optimisation of the CPU is "
           f"about waiting and response time. And the price of SRTF is fairness: its average maximum waiting time ({CPU['SRTF']['max_waiting']}) is only {100 * (CPU['FCFS']['max_waiting'] - CPU['SRTF']['max_waiting']) / CPU['FCFS']['max_waiting']:.0f}% below FCFS's ({CPU['FCFS']['max_waiting']}), "
           "so the longest-waiting job gains little while the short ones gain a lot. For a workload of only short jobs round robin falls behind even FCFS on waiting time: "
           f"SRTF {SHORT['SRTF']['avg_waiting']}, FCFS {SHORT['FCFS']['avg_waiting']}, RR {SHORT['RR']['avg_waiting']}, because a quantum of 4 cuts jobs that would have finished in one turn.")
    r.h(2, "6.4  Choosing the time quantum")
    r.para("Figure 6.4 sweeps the round-robin quantum from 1 to 20 on 300 mixed workloads. The average response time grows steadily with the quantum "
           f"(from {Q[1]['avg_response']} at q = 1 to {Q[20]['avg_response']} at q = 20) and the number of context switches falls from {Q[1]['switches']} to {Q[20]['switches']}. The average waiting time does "
           f"not move in a straight line: it is lowest at q = 5 ({Q[5]['avg_waiting']}) and higher on both sides ({Q[4]['avg_waiting']} at q = 4, {Q[20]['avg_waiting']} at q = 20). The reason is in the "
           "generator: 70% of the jobs have bursts of 1 to 5 units. With q = 5 every short job finishes in one turn and never queues a second time, while a smaller quantum "
           "splits it. This is the rule of thumb of the textbooks, that most CPU bursts should be shorter than the quantum, observed on a generated workload. With a context-switch cost "
           f"of 0.5 time units the combined score of Section 5.5 is also lowest at q = {R['quantum_best_score']} ({Q[R['quantum_best_score']]['score']}), so the optimizer recommends q = {R['quantum_best_score']} for this kind of workload. "
           "A system with different job lengths would get a different answer, which is why the tool sweeps instead of fixing a number.")
    r.figure(A + "chart_quantum.png", "Figure 6.4: Effect of the time quantum on waiting, response and context switches", width_cm=14.5)
    r.h(2, "6.5  Page replacement and the number of frames")
    rows = [[f, f"{100 * MEM[str(f)]['FIFO']:.1f}", f"{100 * MEM[str(f)]['CLOCK']:.1f}", f"{100 * MEM[str(f)]['LRU']:.1f}", f"{100 * MEM[str(f)]['OPT']:.1f}"] for f in (3, 4, 5, 6, 8, 10, 12)]
    r.table("Table 6.3: Page-fault rate (%), mean of 200 reference strings with locality", ["Frames", "FIFO", "CLOCK", "LRU", "OPT"], rows, widths=[2.4, 3.0, 3.0, 3.0, 3.0], size=10.5)
    need = R["frames_for_18pct"]
    r.para(f"Figure 6.5 and Table 6.3 show the fault rate of the four rules on 200 reference strings with locality. The ranking is the same at every number of frames: OPT is lowest, then LRU, CLOCK and FIFO. "
           f"With five frames the fault rates are {100 * MEM['5']['FIFO']:.1f}% for FIFO, {100 * MEM['5']['CLOCK']:.1f}% for CLOCK, {100 * MEM['5']['LRU']:.1f}% for LRU and {100 * MEM['5']['OPT']:.1f}% for OPT, so LRU removes "
           f"{100 * (MEM['5']['FIFO'] - MEM['5']['LRU']) / MEM['5']['FIFO']:.0f}% of the faults of FIFO, and CLOCK, which needs only one bit per page, recovers {100 * (MEM['5']['FIFO'] - MEM['5']['CLOCK']) / (MEM['5']['FIFO'] - MEM['5']['LRU']):.0f}% of that gain. "
           f"Adding frames helps with diminishing returns: to bring the fault rate down to 18% FIFO needs {need['FIFO']} frames, CLOCK {need['CLOCK']} and LRU {need['LRU']}, so a better replacement rule is worth a frame of memory. "
           "The gap between LRU and OPT never closes completely; it is the price of not knowing the future.")
    r.figure(A + "chart_memory.png", "Figure 6.5: Page-fault rate against the number of frames", width_cm=12.0)
    u = R["memory_uniform"]
    r.para(f"Locality is what makes LRU useful. On strings with no locality (every page equally likely) with 8 frames the three real rules are indistinguishable: FIFO {100 * u['FIFO']:.1f}%, LRU {100 * u['LRU']:.1f}%, CLOCK {100 * u['CLOCK']:.1f}%, "
           f"while OPT, which sees the future, achieves {100 * u['OPT']:.1f}%. When the past says nothing about the future, no rule that learns from the past can do better than chance, and the optimizer reports that "
           "LRU's advantage in Table 6.3 belongs to the workload and not to the algorithm alone.")
    r.h(2, "6.6  Belady's anomaly")
    b = R["belady_book"]; an = R["belady_strings_with_anomaly_of_500"]
    r.para(f"On the textbook string 1 2 3 4 1 2 5 1 2 3 4 5 FIFO makes {b['FIFO'][2]} faults with three frames and {b['FIFO'][3]} with four (Figure 6.6): more memory, more faults. CLOCK shows the same behaviour on this string, "
           f"while LRU improves from {b['LRU'][2]} to {b['LRU'][3]} and OPT from {b['OPT'][2]} to {b['OPT'][3]}. The anomaly is not only a textbook curiosity. In 500 random strings of 60 references over 8 pages, FIFO showed it in {an['FIFO']} strings "
           f"and CLOCK in {an['CLOCK']}, while LRU and OPT showed it in none, as they must since they are stack algorithms. It is rare, but it is a reason why the optimizer never treats \"more frames\" as automatically better for FIFO.")
    r.figure(A + "chart_belady.png", "Figure 6.6: Belady's anomaly on the textbook string", width_cm=11.0)
    r.h(2, "6.7  Disk scheduling")
    rows = [[a, DSK["uniform"][a], f'{100 * (1 - DSK["uniform"][a] / DSK["uniform"]["FCFS"]):.0f}%', DSK["clustered"][a], f'{100 * (1 - DSK["clustered"][a] / DSK["clustered"]["FCFS"]):.0f}%'] for a in disk.ALGORITHMS]
    r.table("Table 6.4: Head movement per queue of 20 requests (mean of 300 queues)", ["Algorithm", "Uniform", "Less than FCFS", "Clustered", "Less than FCFS"], rows, widths=[3.0, 2.6, 3.2, 2.6, 3.2], size=10.5)
    r.para(f"Table 6.4 and Figure 6.7 compare the six algorithms on 300 queues of 20 requests. FCFS moves the arm about {DSK['uniform']['FCFS']:.0f} cylinders for a queue of uniformly spread requests, SSTF only {DSK['uniform']['SSTF']:.0f}, "
           f"and LOOK {DSK['uniform']['LOOK']:.0f}: serving the requests in an order that follows the geometry of the disk removes more than 80% of the movement. SSTF is the shortest, but only slightly "
           f"({DSK['uniform']['SSTF']:.0f} against {DSK['uniform']['LOOK']:.0f} for LOOK), and it can starve a request that is far from a busy region, which LOOK cannot because it sweeps the whole disk. SCAN and C-SCAN pay for "
           f"travelling to the ends ({DSK['uniform']['SCAN']:.0f} and {DSK['uniform']['C-SCAN']:.0f}); C-LOOK ({DSK['uniform']['C-LOOK']:.0f}) gives the most uniform waiting among the sweep algorithms at the cost of the return trip. "
           f"When the requests are clustered the differences between the pure sweep algorithms grow: SSTF {DSK['clustered']['SSTF']:.0f}, LOOK {DSK['clustered']['LOOK']:.0f}, C-LOOK {DSK['clustered']['C-LOOK']:.0f}, SCAN {DSK['clustered']['SCAN']:.0f}, because the long trips to the end of the disk are wasted.")
    r.figure(A + "chart_disk.png", "Figure 6.7: Average head movement of the six algorithms", width_cm=12.5)
    r.h(2, "6.8  One scenario, three resources")
    sc = SC
    r.para("To show the optimizer working on the whole system, one scenario was generated from seed 11: eight processes, a reference string of 200 pages with five frames, and 20 disk requests. "
           "Table 6.5 shows the baseline, the recommended choice and the saving for each resource.")
    r.table("Table 6.5: Combined scenario (seed 11)", ["Resource", "Measure", "Baseline", "Recommended", "Result", "Saving"],
            [["CPU", "average waiting time", f"FCFS: {sc['cpu']['baseline']}", sc["cpu"]["choice"], sc["cpu"]["best"], f"{sc['cpu']['gain']:.1f}%"],
             ["Memory", "page faults (5 frames)", f"FIFO: {sc['memory']['baseline']}", sc["memory"]["choice"], sc["memory"]["best"], f"{sc['memory']['gain']:.1f}%"],
             ["I/O", "head movement (cylinders)", f"FCFS: {sc['disk']['baseline']}", sc["disk"]["choice"], sc["disk"]["best"], f"{sc['disk']['gain']:.1f}%"]],
            widths=[1.8, 3.5, 2.5, 2.9, 1.8, 2.5], size=10)
    r.para(f"The CPU and the disk gain most ({sc['cpu']['gain']:.0f}% and {sc['disk']['gain']:.0f}%) because FCFS ignores everything about the work, while memory gains {sc['memory']['gain']:.0f}% because even FIFO "
           "keeps some useful pages. These are the results for one scenario, not a promise: Tables 6.2 to 6.4 give the typical gains over many workloads.")
    r.h(2, "6.9  Browser interface")
    r.para("Figures 6.8 to 6.10 show the three tabs of the browser interface (`python -m resopt.server`). Each tab has an input area filled with an example, a button that runs all algorithms, "
           "a comparison table in which the recommended row is highlighted, and a picture of the result.")
    r.figure(A + "shot_cpu.png", "Figure 6.8: CPU tab: comparison table, recommendation and Gantt chart", width_cm=11.5)
    r.para("In Figure 6.8 five processes with their priorities are compared. SRTF is highlighted: its average waiting time of 6.60 is 42.11% lower than the 11.40 of FCFS, and the explanation notes that long "
           "processes can be starved. The Gantt chart of FCFS runs the processes in order of arrival, while that of SRTF shows P1 pre-empted at time 1 by the shorter P2 and resumed at time 12.")
    r.figure(A + "shot_memory.png", "Figure 6.9: Memory tab: faults of each rule and the frame table of the recommended one", width_cm=11.5)
    r.para("Figure 6.9 repeats the textbook string with three frames. LRU is recommended with 12 faults, 3 above the optimal 9, and 20% fewer faults than FIFO. The frame table below shows, for LRU, the page "
           "referenced at each step (red where a fault occurred) and the content of each frame after the reference.")
    r.figure(A + "shot_disk.png", "Figure 6.10: I/O tab: head movement of each algorithm and the path of the recommended one", width_cm=11.5)
    r.para("Figure 6.10 shows the disk tab on the textbook queue with the head at 53 and the arm moving up first. SSTF is recommended with 236 cylinders, 63.13% less than FCFS's 640, and the path "
           "of the head is drawn with the starting cylinder in orange. The reminder under the table, to check for starvation, appears because the shortest-seek rule can delay far requests.")
    r.h(2, "6.10  Performance")
    r.table("Table 6.6: Time to run all algorithms of one resource", ["Workload", "Time (ms)"], [[p["what"], p["ms"]] for p in R["perf"]], widths=[11.0, 3.0], size=10.5)
    r.para(f"The simulators are fast enough for interactive use: all six CPU algorithms on 200 processes take {R['perf'][2]['ms']:.0f} ms, and the four page-replacement rules on 5,000 references take about {R['perf'][4]['ms']:.0f} ms. "
           "OPT dominates the memory time because it looks ahead in the string, and the pre-emptive CPU algorithms dominate the CPU time because they decide at every time unit. "
           "The times are from one machine and one Python version and show the order of magnitude only.")
    r.h(2, "6.11  Discussion")
    r.para("The results support the aims of the project. The simulators agree with the textbook, and with each other on the properties that theory demands: SRTF is never beaten for waiting time, LRU and OPT never show Belady's anomaly, "
           "OPT is a lower bound, LOOK never exceeds SCAN. On generated workloads the choice of algorithm matters a great deal for waiting time and head movement and less for page faults, and the best algorithm depends on the workload: "
           "round robin wins on response time and loses on waiting, LRU wins only when the program has locality, and SSTF wins on movement but not on fairness. A tool that reports only one metric would hide these trade-offs; "
           "the optimizer reports all of them and recommends on the main one.")
    r.para("The experiments also have limits. The workloads are synthetic and their parameters (70% short jobs, a locality set of five pages) were chosen by the authors, so the absolute numbers would change for other systems; "
           "only the orderings that follow from theory, and the way each trade-off appears, can be expected to carry over. The CPU model gives no cost to a context switch and the disk model ignores rotational delay, which "
           "favours the algorithms that switch or move a lot. Real operating systems also combine these ideas, for example multilevel feedback queues and elevator-style disk schedulers with deadlines, which are beyond this study.")


def chapter7(r):
    H1(r, "7. CONCLUSION", 7)
    r.para("This mini project built a simulator and optimizer for the three resources that an operating system shares: the processor, the memory and the disk. "
           "Six CPU scheduling algorithms, four page-replacement rules and six disk-scheduling algorithms were implemented from their definitions, compared on the same workloads, and "
           "tied together by an optimizer that ranks them, recommends one with its reason, and tunes the round-robin quantum and the number of frames. The simulators reproduce the textbook examples "
           "exactly, and 29 automated tests, including property tests on generated workloads, pass.")
    r.para(f"The experiments show how large and how workload-dependent the differences are. SRTF lowered the average waiting time by {100 * (CPU['FCFS']['avg_waiting'] - CPU['SRTF']['avg_waiting']) / CPU['FCFS']['avg_waiting']:.0f}% against FCFS and was never beaten; "
           f"the best round-robin quantum was 5 because most jobs were that short; LRU removed {100 * (MEM['5']['FIFO'] - MEM['5']['LRU']) / MEM['5']['FIFO']:.0f}% of FIFO's faults on programs with locality and nothing on programs without it; and LOOK or SSTF "
           f"removed more than {100 * (1 - DSK['uniform']['LOOK'] / DSK['uniform']['FCFS']):.0f}% of the head movement of FCFS. No algorithm was best on every measure, which is the reason for an optimizer that reports all of them. "
           "Choosing the right policy for the workload, and not adding hardware, is the cheapest way to make a system faster.")
    r.h(2, "7.1  Limitations")
    r.bullets(["The tool is a simulator: it models time in whole units and does not run inside a real kernel.",
               "Bursts are known in advance, which real schedulers must estimate; processes have no I/O phases of their own.",
               "A context switch costs no time unless a cost is given to the tuning function, and the disk model ignores rotational delay.",
               "Page replacement is studied for one reference string against a fixed number of frames, not for several processes competing for memory.",
               "All disk requests are present at the start; requests that arrive while the arm is moving are not modelled.",
               "The workloads are synthetic with parameters chosen by the authors, so absolute numbers depend on them."])
    r.h(2, "7.2  Future scope")
    r.bullets(["Add multilevel feedback queues, highest-response-ratio-next and real-time schedulers (rate monotonic, earliest deadline first).",
               "Estimate burst lengths by exponential averaging so that SJF and SRTF can be used without knowing the future.",
               "Add process I/O phases, so that CPU, memory and disk are simulated together in one timeline.",
               "Model several processes with working-set or page-fault-frequency allocation, and thrashing.",
               "Replay real traces (for example the page references of a real program or a disk trace) instead of generated workloads.",
               "Add arrival over time for disk requests and starvation measures such as the longest wait.",
               "Report confidence intervals for the generated experiments and allow the user to save and reload workloads."])


def chapter8(r):
    H1(r, "8. REFERENCE", 8)
    refs = [
        "A. Silberschatz, P. B. Galvin and G. Gagne, Operating System Concepts, 10th ed. Hoboken, NJ: Wiley, 2018.",
        "A. S. Tanenbaum and H. Bos, Modern Operating Systems, 4th ed. Boston, MA: Pearson, 2014.",
        "W. Stallings, Operating Systems: Internals and Design Principles, 9th ed. New York, NY: Pearson, 2018.",
        "F. J. Corbató, \"A paging experiment with the Multics system,\" in In Honor of Philip M. Morse, H. Feshbach and K. U. Ingard, Eds. Cambridge, MA: MIT Press, 1969, pp. 217–228.",
        "L. A. Belady, R. A. Nelson and G. S. Shedler, \"An anomaly in space-time characteristics of certain programs running in a paging machine,\" Communications of the ACM, vol. 12, no. 6, pp. 349–353, 1969.",
        "L. Schrage, \"A proof of the optimality of the shortest remaining processing time discipline,\" Operations Research, vol. 16, no. 3, pp. 687–690, 1968.",
        "P. J. Denning, \"Effects of scheduling on file memory operations,\" in Proceedings of the AFIPS Spring Joint Computer Conference, 1967, pp. 9–21.",
        "R. L. Mattson, J. Gecsei, D. R. Slutz and I. L. Traiger, \"Evaluation techniques for storage hierarchies,\" IBM Systems Journal, vol. 9, no. 2, pp. 78–117, 1970.",
        "P. J. Denning, \"The working set model for program behavior,\" Communications of the ACM, vol. 11, no. 5, pp. 323–333, 1968.",
        "L. A. Belady, \"A study of replacement algorithms for a virtual-storage computer,\" IBM Systems Journal, vol. 5, no. 2, pp. 78–101, 1966.",
    ]
    for i, t in enumerate(refs, 1):
        p = r.para(f"[{i}]  {t}", size=12, spacing=1.15, after=5, indent=1.0)
        p.paragraph_format.first_line_indent = r.cm(-1.0)
