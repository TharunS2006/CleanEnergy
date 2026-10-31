import json, math, random, threading, unittest, urllib.request
from http.server import ThreadingHTTPServer

from vmdr import avail, sim, dr, backup, cli, server


class AvailabilityMath(unittest.TestCase):
    def test_single_component(self):
        a = avail.availability(2000, 4)
        self.assertAlmostEqual(a, 2000 / 2004)
        self.assertAlmostEqual(avail.downtime_minutes_per_year(0.9999), 52.56, places=2)
        self.assertAlmostEqual(avail.nines(0.999), 3.0)
        self.assertEqual(avail.nines(1.0), math.inf)

    def test_series_and_parallel(self):
        self.assertAlmostEqual(avail.series(0.9, 0.9), 0.81)
        self.assertAlmostEqual(avail.parallel(0.9, 0.9), 0.99)
        self.assertAlmostEqual(avail.parallel(0.9, 0.9, 0.9), 0.999)

    def test_k_of_n(self):
        self.assertAlmostEqual(avail.k_of_n(2, 3, 0.9), 0.972)
        self.assertAlmostEqual(avail.k_of_n(1, 2, 0.9), avail.parallel(0.9, 0.9))
        self.assertAlmostEqual(avail.k_of_n(3, 3, 0.9), 0.729)
        with self.assertRaises(ValueError): avail.k_of_n(4, 3, 0.9)

    def test_bad_input(self):
        with self.assertRaises(ValueError): avail.availability(0, 1)
        with self.assertRaises(ValueError): avail.availability(10, -1)

    def test_markov_pair_limits(self):
        u0 = avail.active_passive_unavailability(2000, 4, 1e-6)           # instant failover: only double failures remain
        a = avail.availability(2000, 4)
        self.assertLess(u0, 1 - avail.availability(2000, 4))              # far better than one node
        self.assertGreater(u0, 1 - avail.parallel(a, a) - 1e-9)           # never better than an ideal active-active pair
        slow = avail.active_passive_unavailability(2000, 4, 1.0)
        self.assertGreater(slow, u0)                                      # a slower failover costs availability

    def test_sla_table(self):
        d = avail.sla_downtime(0.999)
        self.assertAlmostEqual(d["per_year"], 525.6, places=1)


class IntervalTests(unittest.TestCase):
    def test_union_and_intersect(self):
        self.assertEqual(sim.union([(1, 3), (2, 5)], [(7, 8)]), [(1, 5), (7, 8)])
        self.assertEqual(sim.intersect([(0, 5), (8, 10)], [(3, 9)]), [(3, 5), (8, 9)])
        self.assertEqual(sim.total([(1, 3), (4, 5)]), 3)

    def test_renewal_is_ordered_and_inside_horizon(self):
        iv = sim.renewal(random.Random(1), 100, 5, 10000)
        self.assertTrue(all(a < b for a, b in iv))
        self.assertTrue(all(iv[i][1] <= iv[i + 1][0] for i in range(len(iv) - 1)))
        self.assertLessEqual(iv[-1][1], 10000)


class FailoverStateMachine(unittest.TestCase):
    def test_simple_failover(self):
        self.assertEqual(sim.active_passive_down([(10, 20)], [], 1.0, 100), [(10, 11)])

    def test_standby_fails_after_the_switch(self):
        out = sim.active_passive_down([(10, 20)], [(12, 15)], 1.0, 100)
        self.assertEqual(out, [(10, 11), (12, 15)])

    def test_target_fails_during_the_switch(self):
        out = sim.active_passive_down([(10, 20)], [(10.5, 11.5)], 1.0, 100)
        self.assertEqual(out, [(10, 12.5)])

    def test_both_down_waits_for_first_repair(self):
        out = sim.active_passive_down([(10, 20)], [(9, 30)], 1.0, 100)
        self.assertEqual(out, [(10, 20)])

    def test_original_back_before_switch_ends(self):
        out = sim.active_passive_down([(10, 10.5)], [], 1.0, 100)
        self.assertEqual(out, [(10, 10.5)])

    def test_unfinished_outage_is_closed_at_the_horizon(self):
        self.assertEqual(sim.active_passive_down([(90, 100)], [(90, 100)], 1.0, 100), [(90, 100)])


class DisasterRecovery(unittest.TestCase):
    def test_takeover_time(self):
        down, tk = sim.dr_takeover([], [(100, 160)], [], 0.1, 0.9, 1000)
        self.assertEqual(down, [(100, 101)]); self.assertEqual(len(tk), 1)

    def test_short_outage_no_takeover(self):
        down, tk = sim.dr_takeover([], [(100, 100.5)], [], 0.1, 0.9, 1000)
        self.assertEqual((down, tk), ([(100, 100.5)], []))

    def test_dr_region_down_at_takeover(self):
        down, tk = sim.dr_takeover([], [(100, 160)], [(100.5, 130)], 0.1, 0.9, 1000)
        self.assertEqual(down, [(100, 130)]); self.assertEqual(tk, [])

    def test_dr_region_fails_while_carrying_the_service(self):
        down, tk = sim.dr_takeover([], [(100, 160)], [(120, 125)], 0.1, 0.9, 1000)
        self.assertEqual(down, [(100, 101), (120, 125)])

    def test_data_loss_means(self):
        rng = random.Random(3)
        wm = dr.TIERS["warm-standby"]; br = dr.TIERS["backup-restore"]
        a = [dr.sample_data_loss_minutes(wm, rng) for _ in range(40000)]
        b = [dr.sample_data_loss_minutes(br, rng) for _ in range(40000)]
        self.assertAlmostEqual(sum(a) / len(a), wm.rpo_mean_minutes, delta=0.05 * wm.rpo_mean_minutes)
        self.assertAlmostEqual(sum(b) / len(b), br.rpo_mean_minutes, delta=0.03 * br.rpo_mean_minutes)

    def test_tiers_are_ordered_by_speed_and_cost(self):
        t = [dr.TIERS[k] for k in ("backup-restore", "pilot-light", "warm-standby", "multi-active")]
        self.assertTrue(all(a.restore_minutes > b.restore_minutes for a, b in zip(t, t[1:])))
        self.assertTrue(all(a.extra_cost < b.extra_cost for a, b in zip(t, t[1:])))
        self.assertTrue(all(a.rpo_mean_minutes > b.rpo_mean_minutes for a, b in zip(t, t[1:])))


class SimulationAgainstTheory(unittest.TestCase):
    """The simulation must reproduce the closed-form results; this is the main evidence that it is right."""
    @classmethod
    def setUpClass(cls):
        cls.p = sim.Params()
        cls.w = sim.make_world(cls.p, 15000, 7)

    def test_single_vm_matches_series_formula(self):
        p = self.p
        exact = avail.series(avail.availability(p.host_mtbf, p.host_mttr), avail.availability(p.zone_mtbf, p.zone_mttr), avail.availability(p.region_mtbf, p.region_mttr))
        got = sim.run("single", p, self.w)["availability"]
        self.assertAlmostEqual(1 - got, 1 - exact, delta=0.04 * (1 - exact))

    def test_active_active_matches_formula(self):
        p = self.p
        inst = avail.series(avail.availability(p.host_mtbf, p.host_mttr), avail.availability(p.zone_mtbf, p.zone_mttr))
        exact = avail.series(avail.parallel(inst, inst), avail.availability(p.region_mtbf, p.region_mttr))
        got = sim.run("aa-two-zones", p, self.w)["availability"]
        self.assertAlmostEqual(1 - got, 1 - exact, delta=0.05 * (1 - exact))

    def test_active_passive_matches_markov_model(self):
        p = sim.Params(zone_mtbf=1e12, region_mtbf=1e12)
        w = sim.make_world(p, 30000, 5)
        got = 1 - sim.run("ap-one-zone", p, w)["availability"]
        exact = avail.active_passive_unavailability(p.host_mtbf, p.host_mttr, p.failover_minutes / 60.0)
        self.assertAlmostEqual(got, exact, delta=0.08 * exact)

    def test_restart_removes_most_of_the_host_repair_time(self):
        s, r = sim.run("single", self.p, self.w), sim.run("restart", self.p, self.w)
        self.assertLess(r["downtime_min_per_year"], 0.35 * s["downtime_min_per_year"])

    def test_more_redundancy_never_hurts_on_the_same_failures(self):
        d = {k: sim.run(k, self.p, self.w, dr.TIERS["warm-standby"])["downtime_min_per_year"] for k in sim.STRATEGIES}
        self.assertLessEqual(d["aa-two-zones"], d["single"])
        self.assertLessEqual(d["aa-dr"], d["aa-two-zones"])
        self.assertLessEqual(d["ap-two-zones"], d["ap-one-zone"] + 1e-9)

    def test_region_disasters_limit_everything_without_a_dr_region(self):
        floor = 60 * self.p.region_mttr / self.p.region_mtbf * 8760
        for k in ("single", "restart", "ap-two-zones", "aa-two-zones"):
            self.assertGreater(sim.run(k, self.p, self.w)["downtime_min_per_year"], 0.9 * floor)

    def test_same_seed_same_result(self):
        a = sim.compare(self.p, 500, 3); b = sim.compare(self.p, 500, 3)
        self.assertEqual({k: v["downtime_min_per_year"] for k, v in a.items()}, {k: v["downtime_min_per_year"] for k, v in b.items()})

    def test_unknown_strategy(self):
        with self.assertRaises(ValueError): sim.run("magic", self.p, self.w)
        with self.assertRaises(ValueError): sim.run("aa-dr", self.p, self.w)


class BackupTests(unittest.TestCase):
    def test_formula_and_simulation_agree(self):
        self.assertAlmostEqual(backup.mean_data_age_minutes(1440, 1.0), 720)
        sim_mean = backup.simulate_data_age(1440, 0.9, 100000)
        self.assertAlmostEqual(sim_mean, backup.mean_data_age_minutes(1440, 0.9), delta=0.02 * backup.mean_data_age_minutes(1440, 0.9))

    def test_percentile(self):
        self.assertEqual(backup.percentile_data_age_minutes(1440, 1.0), 1440)
        self.assertEqual(backup.percentile_data_age_minutes(1440, 0.98), 3 * 1440)

    def test_restore_time(self):
        self.assertAlmostEqual(backup.restore_minutes(1024, 100, 20, 10), 1024 * 1024 / 100 / 60 + 30)
        with self.assertRaises(ValueError): backup.restore_minutes(0, 100)


class PlannerTests(unittest.TestCase):
    def test_modest_target_is_met_cheaply(self):
        r = dr.plan(0.999)
        self.assertEqual((r["recommended"]["strategy"], r["recommended"]["cost"]), ("restart", 1.1))

    def test_four_nines_needs_a_dr_region(self):
        r = dr.plan(0.9999)
        self.assertEqual(r["recommended"]["strategy"], "aa-dr")

    def test_recovery_time_limit_selects_warm_standby(self):
        r = dr.plan(0.9999, rto_minutes=60, rpo_minutes=15)
        self.assertEqual(r["recommended"]["tier"], "warm-standby")

    def test_tight_data_loss_selects_multi_region(self):
        self.assertEqual(dr.plan(0.9999, rto_minutes=60, rpo_minutes=0.5)["recommended"]["tier"], "multi-active")

    def test_impossible_target_has_no_recommendation(self):
        self.assertIsNone(dr.plan(0.9999999)["recommended"])

    def test_every_rejected_option_has_a_reason(self):
        for row in dr.plan(0.9999, 60, 15)["rows"]:
            self.assertEqual(row["meets"], not row["why_not"])


class InterfaceTests(unittest.TestCase):
    def test_cli(self):
        self.assertEqual(cli.main(["avail"]), 0)
        self.assertEqual(cli.main(["plan", "--target", "0.999"]), 0)

    def test_server(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        def post(path, body):
            req = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req))
        try:
            a = post("/api/avail", {"mtbf": 2000, "mttr": 4})
            c = post("/api/compare", {"years": 300, "tier": "pilot-light"})
            p = post("/api/plan", {"target": 0.9999, "rto": 60, "rpo": 15})
            b = post("/api/backup", {"interval": 1440, "success": 0.98})
            try:
                post("/api/avail", {"mtbf": 0, "mttr": 4}); code = None
            except urllib.error.HTTPError as e:
                code = e.code
        finally:
            srv.shutdown(); srv.server_close()
        self.assertAlmostEqual(a["availability"], 2000 / 2004)
        self.assertEqual(set(c["results"]), set(sim.STRATEGIES))
        self.assertEqual(p["recommended"]["tier"], "warm-standby")
        self.assertAlmostEqual(b["mean"], 749.4, places=1)
        self.assertEqual(code, 400)


if __name__ == "__main__":
    unittest.main()
