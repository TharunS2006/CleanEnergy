import json, threading, unittest, urllib.request
from http.server import ThreadingHTTPServer

from resopt import cpu, memory, disk, optimizer, server
from resopt.cpu import Proc
from resopt.workloads import cpu_workload, page_refs, disk_requests
from resopt import cli

BOOK = [Proc("P1", 0, 24), Proc("P2", 0, 3), Proc("P3", 0, 3)]
REFS = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
QUEUE = [98, 183, 37, 122, 14, 124, 65, 67]


class CpuTests(unittest.TestCase):
    def test_textbook_waiting_times(self):
        w = {a: cpu.simulate(a, BOOK, 4)["metrics"]["avg_waiting"] for a in ("FCFS", "SJF", "SRTF", "RR")}
        self.assertEqual((w["FCFS"], w["SJF"], w["SRTF"]), (17, 3, 3))
        self.assertAlmostEqual(w["RR"], 17 / 3, places=6)

    def test_round_robin_gantt(self):
        self.assertEqual(cpu.simulate("RR", BOOK, 4)["gantt"], [("P1", 0, 4), ("P2", 4, 7), ("P3", 7, 10), ("P1", 10, 30)])

    def test_srtf_preempts_a_longer_job(self):
        p = [Proc("A", 0, 7), Proc("B", 2, 2)]
        self.assertEqual(cpu.simulate("SRTF", p)["gantt"], [("A", 0, 2), ("B", 2, 4), ("A", 4, 9)])
        self.assertEqual(cpu.simulate("SJF", p)["gantt"], [("A", 0, 7), ("B", 7, 9)])

    def test_priority_orders_by_priority(self):
        p = [Proc("L", 0, 5, 3), Proc("H", 0, 5, 1), Proc("M", 0, 5, 2)]
        self.assertEqual([g[0] for g in cpu.simulate("PRIORITY", p)["gantt"]], ["H", "M", "L"])

    def test_preemptive_priority(self):
        p = [Proc("L", 0, 6, 3), Proc("H", 2, 2, 1)]
        self.assertEqual(cpu.simulate("PRIORITY-P", p)["gantt"], [("L", 0, 2), ("H", 2, 4), ("L", 4, 8)])

    def test_idle_gap_lowers_utilisation(self):
        r = cpu.simulate("FCFS", [Proc("A", 0, 2), Proc("B", 6, 2)])
        self.assertIn(("idle", 2, 6), r["gantt"])
        self.assertAlmostEqual(r["metrics"]["utilisation"], 0.5)

    def test_time_accounting_is_consistent(self):
        for kind in ("mixed", "short", "long"):
            for seed in range(20):
                procs = cpu_workload(7, seed, kind)
                for a in cpu.ALGORITHMS:
                    r = cpu.simulate(a, procs, 3)
                    for row in r["rows"]:
                        self.assertEqual(row["waiting"], row["turnaround"] - row["burst"])
                        self.assertGreaterEqual(row["waiting"], 0)
                    self.assertEqual(sum(e - s for p, s, e in r["gantt"] if p != "idle"), sum(p.burst for p in procs))

    def test_srtf_never_beaten_on_average_waiting(self):
        """SRTF is provably optimal for average waiting time, so no algorithm may beat it on any workload."""
        for seed in range(150):
            runs = cpu.compare(cpu_workload(8, seed, "mixed"), 4)
            best = runs["SRTF"]["metrics"]["avg_waiting"]
            self.assertTrue(all(r["metrics"]["avg_waiting"] >= best - 1e-9 for r in runs.values()), seed)

    def test_bad_input(self):
        for bad in ([], [Proc("A", 0, 0)], [Proc("A", 0, 1), Proc("A", 1, 1)]):
            with self.assertRaises(ValueError): cpu.simulate("FCFS", bad)
        with self.assertRaises(ValueError): cpu.simulate("RR", BOOK, 0)


class MemoryTests(unittest.TestCase):
    def test_textbook_fault_counts(self):
        self.assertEqual({a: memory.simulate(a, REFS, 3)["faults"] for a in ("FIFO", "LRU", "OPT")}, {"FIFO": 15, "LRU": 12, "OPT": 9})

    def test_beladys_anomaly_for_fifo(self):
        s = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        self.assertEqual((memory.simulate("FIFO", s, 3)["faults"], memory.simulate("FIFO", s, 4)["faults"]), (9, 10))
        self.assertEqual((memory.simulate("LRU", s, 3)["faults"], memory.simulate("LRU", s, 4)["faults"]), (10, 8))

    def test_stack_algorithms_have_no_anomaly(self):
        for seed in range(60):
            refs = page_refs(80, 10, seed, locality=False)
            for a in ("LRU", "OPT"):
                f = [memory.simulate(a, refs, k)["faults"] for k in range(1, 9)]
                self.assertTrue(all(x >= y for x, y in zip(f, f[1:])), (a, seed, f))

    def test_opt_is_a_lower_bound(self):
        for seed in range(40):
            refs = page_refs(100, 12, seed)
            opt = memory.simulate("OPT", refs, 4)["faults"]
            self.assertTrue(all(memory.simulate(a, refs, 4)["faults"] >= opt for a in ("FIFO", "LRU", "CLOCK")))

    def test_enough_frames_means_only_cold_faults(self):
        self.assertEqual(memory.simulate("LRU", REFS, 8)["faults"], len(set(REFS)))

    def test_clock_gives_a_second_chance(self):
        r = memory.simulate("CLOCK", [1, 2, 3, 4, 2, 5], 3)       # page 2 was used again, so it survives; FIFO would evict it
        self.assertEqual(r["steps"][-1]["victim"], 3)
        self.assertEqual(memory.simulate("FIFO", [1, 2, 3, 4, 2, 5], 3)["steps"][-1]["victim"], 2)

    def test_steps_record_frames(self):
        r = memory.simulate("FIFO", [1, 2, 1, 3], 2)
        self.assertEqual([s["fault"] for s in r["steps"]], [True, True, False, True])
        self.assertEqual(r["steps"][-1]["frames"], [2, 3])


class DiskTests(unittest.TestCase):
    def test_textbook_totals_moving_down_first(self):
        t = {a: disk.simulate(a, QUEUE, 53, 200, -1)["total"] for a in disk.ALGORITHMS}
        self.assertEqual(t, {"FCFS": 640, "SSTF": 236, "SCAN": 236, "C-SCAN": 386, "LOOK": 208, "C-LOOK": 326})

    def test_totals_moving_up_first(self):
        t = {a: disk.simulate(a, QUEUE, 53, 200, 1)["total"] for a in disk.ALGORITHMS}
        self.assertEqual(t, {"FCFS": 640, "SSTF": 236, "SCAN": 331, "C-SCAN": 382, "LOOK": 299, "C-LOOK": 322})

    def test_every_request_is_visited(self):
        for seed in range(30):
            reqs, head = disk_requests(15, 200, seed)
            for a in disk.ALGORITHMS:
                path = disk.simulate(a, reqs, head)["path"]
                self.assertTrue(set(reqs) <= set(path), (a, seed))
                self.assertTrue(all(0 <= c < 200 for c in path))

    def test_look_never_moves_more_than_scan(self):
        for seed in range(50):
            reqs, head = disk_requests(12, 200, seed)
            self.assertLessEqual(disk.simulate("LOOK", reqs, head)["total"], disk.simulate("SCAN", reqs, head)["total"])

    def test_bad_input(self):
        with self.assertRaises(ValueError): disk.simulate("SCAN", [500], 10)
        with self.assertRaises(ValueError): disk.simulate("SCAN", [], 10)


class OptimizerTests(unittest.TestCase):
    def test_cpu_recommendation(self):
        r = optimizer.recommend_cpu(BOOK)
        self.assertIn(r["recommended"], ("SJF", "SRTF"))
        self.assertAlmostEqual(r["improvement"], 100 * (17 - 3) / 17)

    def test_memory_recommendation_is_not_opt(self):
        r = optimizer.recommend_memory(REFS, 3)
        self.assertEqual((r["recommended"], r["optimal_faults"], r["gap_to_optimal"]), ("LRU", 9, 3))

    def test_disk_recommendation(self):
        self.assertEqual(optimizer.recommend_disk(QUEUE, 53)["recommended"], "SSTF")

    def test_quantum_tuning_returns_a_tested_quantum(self):
        t = optimizer.tune_quantum(cpu_workload(8, 3), range(1, 11))
        self.assertIn(t["best_quantum"], range(1, 11))
        self.assertEqual(len(t["rows"]), 10)

    def test_frames_needed(self):
        t = optimizer.tune_frames(page_refs(200, 20, 1), "LRU", 20, 0.2)
        self.assertEqual(t["curve"][-1][1] <= 0.2, t["frames_needed"] is not None)

    def test_scenario_gains_are_not_negative(self):
        procs = cpu_workload(8, 5); refs = page_refs(200, 20, 5); reqs, head = disk_requests(20, 200, 5)
        s = optimizer.optimise(procs, refs, 5, reqs, head)
        self.assertTrue(all(v["gain"] >= 0 for v in s.values()))


class InterfaceTests(unittest.TestCase):
    def test_cli(self):
        self.assertEqual(cli.main(["demo"]), 0)

    def test_server(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        def post(path, body):
            req = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req))
        try:
            c = post("/api/cpu", {"procs": [{"pid": "P1", "arrival": 0, "burst": 24}, {"pid": "P2", "arrival": 0, "burst": 3}, {"pid": "P3", "arrival": 0, "burst": 3}], "quantum": 4})
            m = post("/api/memory", {"refs": REFS, "frames": 3})
            d = post("/api/disk", {"requests": QUEUE, "head": 53})
            try:
                post("/api/disk", {"requests": [999], "head": 1})
                bad = None
            except urllib.error.HTTPError as e:
                bad = e.code
        finally:
            srv.shutdown(); srv.server_close()
        self.assertEqual(c["runs"]["FCFS"]["metrics"]["avg_waiting"], 17)
        self.assertEqual(m["runs"]["LRU"]["faults"], 12)
        self.assertEqual(d["runs"]["SSTF"]["total"], 236)
        self.assertEqual(bad, 400)


if __name__ == "__main__":
    unittest.main()
