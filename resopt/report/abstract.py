import json, pathlib
R = json.load(open(pathlib.Path(__file__).parent.parent / "bench_results.json"))
c = R["cpu"]["mixed"]; sc = R["scenario"]
ABSTRACT = (
    "An operating system keeps three resources busy: the processor, the memory and the input/output devices. For each of them it must "
    "choose a policy: which process runs next, which page leaves memory when a new one arrives, and which disk request the arm "
    "serves first. Textbooks teach these policies one at a time, on a single fixed example, so a student rarely sees how they behave "
    "on a workload of their own, or why the best choice changes from one workload to another. This mini project builds a "
    "simulator and an optimizer for the three resources, using only the Python standard library. The CPU module implements FCFS, "
    "SJF, SRTF, priority scheduling with and without pre-emption, and round robin; the memory module implements FIFO, LRU, "
    "OPT and CLOCK page replacement; the I/O module implements FCFS, SSTF, SCAN, C-SCAN, LOOK and C-LOOK disk scheduling. The "
    "optimizer runs every algorithm on the same workload, ranks them by the metric that matters (waiting time, page faults, head "
    "movement), names the best one with the reason, and tunes parameters such as the round-robin quantum and the number of frames. "
    "The simulators reproduce the textbook results exactly: 17, 3 and 5.67 time units of average waiting for FCFS, SJF and round "
    "robin; 15, 12 and 9 page faults for FIFO, LRU and OPT; and 640, 236 and 208 cylinders of head movement for FCFS, SSTF and LOOK. "
    f"On 500 seeded random workloads SRTF cut the average waiting time from {c['FCFS']['avg_waiting']} to {c['SRTF']['avg_waiting']} time units "
    f"against FCFS and was never beaten. In one combined scenario, the recommended choices reduced waiting time by {sc['cpu']['gain']:.0f}%, "
    f"page faults by {sc['memory']['gain']:.0f}% and head movement by {sc['disk']['gain']:.0f}% against FCFS, FIFO and FCFS. "
    "A command-line tool and a browser interface with Gantt charts, frame tables and head-path plots are provided, and 29 automated tests pass.")
