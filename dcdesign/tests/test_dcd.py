import json, random, threading, unittest, urllib.request
from http.server import ThreadingHTTPServer

from dcd import model, capacity, security, resilience, designs, evaluate, cli, server
from dcd.model import Host, VM, Rule, Design


def tiny(hosts, vms, placement, **kw):
    d = Design("tiny", hosts, vms, kw.pop("rules", designs.policy_rules()), kw.pop("default_action", "deny"), kw.pop("edge", ("FW1", "FW2")),
               kw.pop("arrays", {"S1": True}), kw.pop("vm_array", {}), {}, placement)
    return d


def H(name, rack="R1", feeds=("A", "B"), sw=("S1", "S2"), cool=("C1", "C2"), cpu=32, ram=128):
    return Host(name, cpu, ram, rack, feeds, sw, cool)


class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.hosts = [H(f"h{i}") for i in range(4)]

    def test_never_exceeds_capacity_and_respects_groups(self):
        rng = random.Random(4)
        for _ in range(60):
            vms = [VM(f"v{i}", rng.randint(1, 8), rng.choice([2, 4, 8, 16, 32]), "app", f"g{i // 2}") for i in range(rng.randint(5, 30))]
            for alg in ("ff", "bf", "ffd"):
                pl, _ = capacity.place(vms, self.hosts, alg)
                used = {}
                for v in vms:
                    if v.name in pl:
                        u = used.setdefault(pl[v.name], [0, 0, set()])
                        self.assertNotIn(v.group, u[2]); u[2].add(v.group); u[0] += v.cpu; u[1] += v.ram
                self.assertTrue(all(u[0] <= 32 and u[1] <= 128 for u in used.values()))

    def test_ffd_uses_no_more_hosts_than_the_given_order_on_a_bad_order(self):
        vms = [VM("s1", 16, 16, "app", "a"), VM("s2", 16, 16, "app", "b"), VM("l1", 17, 16, "app", "c"), VM("l2", 17, 16, "app", "d")]
        hosts = [H(f"h{i}") for i in range(6)]
        n = lambda alg: len(set(capacity.place(vms, hosts, alg)[0].values()))
        self.assertLessEqual(n("ffd"), n("ff"))
        self.assertEqual(n("ffd"), 3)

    def test_anti_affinity_forces_separate_hosts(self):
        vms = [VM("a1", 2, 4, "web", "g"), VM("a2", 2, 4, "web", "g")]
        pl, un = capacity.place(vms, self.hosts, "ffd")
        self.assertNotEqual(pl["a1"], pl["a2"]); self.assertEqual(un, [])
        _, un = capacity.place(vms, [H("only")], "ffd")
        self.assertEqual(len(un), 1)

    def test_replicas_prefer_different_racks(self):
        hosts = [H("h1", "R1"), H("h2", "R1"), H("h3", "R2")]
        pl, _ = capacity.place([VM("a1", 2, 4, "web", "g"), VM("a2", 2, 4, "web", "g")], hosts, "ffd")
        self.assertNotEqual({"h1": "R1", "h2": "R1", "h3": "R2"}[pl["a1"]], {"h1": "R1", "h2": "R1", "h3": "R2"}[pl["a2"]])

    def test_too_big_is_unplaced(self):
        _, un = capacity.place([VM("big", 64, 8, "app", "g")], self.hosts, "ffd")
        self.assertEqual(un, ["big"])

    def test_lower_bound(self):
        vms = [VM(f"v{i}", 8, 16, "app", f"g{i}") for i in range(10)]
        self.assertEqual(capacity.lower_bound_hosts(vms, 32, 128), 3)

    def test_n_plus_one(self):
        vms = [VM(f"v{i}", 16, 16, "app", f"g{i}") for i in range(4)]
        two = [H("h1"), H("h2")]; three = [H("h1"), H("h2"), H("h3")]
        d2 = tiny(two, vms, capacity.place(vms, two)[0]); d3 = tiny(three, vms, capacity.place(vms, three)[0])
        self.assertFalse(capacity.n_plus_one(d2)["ok"]); self.assertTrue(capacity.n_plus_one(d3)["ok"])


class FirewallTests(unittest.TestCase):
    def test_first_match_and_default(self):
        d = tiny([], [], {}, rules=[Rule("internet", "db", "5432", "deny"), Rule("any", "any", "any", "allow")])
        self.assertFalse(security.allowed(d, "internet", "db", "5432"))
        self.assertTrue(security.allowed(d, "internet", "dmz", "443"))
        d.rules = []; d.default_action = "deny"; self.assertFalse(security.allowed(d, "app", "db", "5432"))
        d.default_action = "allow"; self.assertTrue(security.allowed(d, "app", "db", "5432"))

    def test_intended_policy_is_clean(self):
        d = tiny([], [], {})
        self.assertEqual(security.findings(d), [])
        self.assertEqual(security.attack_paths(d)["db"]["shortest"], 3)
        self.assertIsNone(security.attack_paths(d)["mgmt"]["shortest"])

    def kinds(self, d):
        return {f["kind"] for f in security.findings(d)}

    def test_every_injected_fault_is_detected(self):
        def with_rules(extra, default="deny"):
            d = tiny([], [], {}); d.rules = d.rules + extra; d.default_action = default; return d
        cases = {"any-any": with_rules([Rule("any", "any", "any", "allow")]), "unauthorised-flow": with_rules([Rule("internet", "db", "5432", "allow")]),
                 "broad-rule": with_rules([Rule("dmz", "any", "any", "allow")]), "default-allow": with_rules([], "allow"),
                 "unencrypted": with_rules([]), "shadowed-rule": with_rules([Rule("internet", "dmz", "443", "deny")])}
        cases["unencrypted"].rules[0].encrypted = False
        for kind, d in cases.items():
            self.assertIn(kind, self.kinds(d), kind)

    def test_blocked_intended_flow_is_reported(self):
        d = tiny([], [], {}); d.rules = [r for r in d.rules if r.dst != "app"]
        self.assertIn("missing-flow", self.kinds(d))

    def test_internet_to_database_is_critical(self):
        d = tiny([], [], {}); d.rules.append(Rule("internet", "db", "5432", "allow"))
        f = [x for x in security.findings(d) if x["kind"] == "unauthorised-flow"][0]
        self.assertEqual(f["severity"], "critical")
        self.assertEqual(security.attack_paths(d)["db"]["shortest"], 1)

    def test_score_orders_the_designs(self):
        s = {k: security.evaluate(designs.reference_design(k))["score"] for k in ("basic", "segmented", "resilient")}
        self.assertLess(s["basic"], 20); self.assertLess(s["basic"], s["segmented"]); self.assertLess(s["segmented"], s["resilient"])

    def test_hardening_score(self):
        d = tiny([], [], {}); d.hardening = {}
        self.assertEqual(security.hardening(d)["score"], 0)
        d.hardening = {k: True for k in model.HARDENING_ITEMS}
        self.assertEqual(security.hardening(d)["score"], 100)


class FailureScenarioTests(unittest.TestCase):
    def build(self, **hostkw):
        hosts = [H("h1", "R1", **hostkw), H("h2", "R2", **hostkw), H("h3", "R2", **hostkw)]
        vms = [VM("w1", 4, 8, "web", "web-1"), VM("w2", 4, 8, "web", "web-1"), VM("d1", 8, 32, "db", "db-1", True), VM("d2", 8, 32, "db", "db-1", True)]
        pl, _ = capacity.place(vms, hosts, "ffd")
        return tiny(hosts, vms, pl, vm_array={v.name: "S1" for v in vms})

    def test_dual_power_survives_one_feed(self):
        self.assertTrue(resilience.scenario(self.build(), {("feed", "A")})["tolerated"])

    def test_single_power_feed_is_a_single_point_of_failure(self):
        s = resilience.scenario(self.build(feeds=("A",)), {("feed", "A")})
        self.assertFalse(s["tolerated"]); self.assertEqual(s["hosts_down"], 3)

    def test_single_firewall_fails_everything(self):
        d = self.build(); d.edge = ("FW1",)
        self.assertFalse(resilience.scenario(d, {("edge", "FW1")})["tolerated"])
        d.edge = ("FW1", "FW2"); self.assertTrue(resilience.scenario(d, {("edge", "FW1")})["tolerated"])

    def test_unmirrored_array_takes_down_its_vms(self):
        d = self.build(); d.arrays = {"S1": False}
        s = resilience.scenario(d, {("array", "S1")})
        self.assertFalse(s["tolerated"]); self.assertEqual(s["vms_down"], 4)

    def test_two_failures_can_defeat_a_dual_path(self):
        d = self.build()
        self.assertFalse(resilience.scenario(d, {("feed", "A"), ("feed", "B")})["tolerated"])

    def test_restart_uses_free_capacity_only(self):
        d = self.build()
        s = resilience.scenario(d, {("host", d.placement["d1"])})
        self.assertTrue(s["tolerated"]); self.assertEqual(s["vms_affected"], s["vms_restarted"] + s["vms_down"])

    def test_component_list_and_spof_filter(self):
        d = self.build(feeds=("A",))
        comps = resilience.components(d)
        self.assertIn(("feed", "A"), comps); self.assertIn(("rack", "R1"), comps)
        rows = resilience.single_failures(d)
        self.assertIn("feed A", [r["component"] for r in resilience.spofs(rows)])


class AvailabilitySimulation(unittest.TestCase):
    def one_vm(self, params):
        hosts = [H("h1", "R1", ("A",), ("S1",), ("C1",))]
        vms = [VM("v1", 2, 4, "web", "web-1")]
        return tiny(hosts, vms, {"v1": "h1"}, edge=("FW1",), arrays={"S1": False}, vm_array={"v1": "S1"})

    def test_single_vm_matches_the_series_formula(self):
        d = self.one_vm(None)
        got = resilience.availability(d, 6000, 3)["tiers"]["web"]["availability"]
        p = resilience.FAILURE_PARAMS
        exact = 1.0
        for kind in ("host", "rack", "feed", "switch", "cooling", "edge", "array"):
            exact *= p[kind][0] / (p[kind][0] + p[kind][1])
        self.assertAlmostEqual(1 - got, 1 - exact, delta=0.08 * (1 - exact))

    def test_two_replicas_on_separate_racks_match_the_parallel_formula(self):
        hosts = [H("h1", "R1", ("A",), ("S1",), ("C1",)), H("h2", "R2", ("A",), ("S1",), ("C1",))]
        vms = [VM("v1", 2, 4, "web", "g"), VM("v2", 2, 4, "web", "g")]
        quiet = {k: (1e12, 1.0) for k in resilience.FAILURE_PARAMS}; quiet["host"] = (2000.0, 4.0)
        d = tiny(hosts, vms, {"v1": "h1", "v2": "h2"}, edge=("FW1",), arrays={"S1": True}, vm_array={"v1": "S1", "v2": "S1"})
        got = resilience.availability(d, 40000, 5, quiet)["groups"]["g"]["availability"]
        a = 2000 / 2004
        self.assertAlmostEqual(1 - got, (1 - a) ** 2, delta=0.12 * (1 - a) ** 2)

    def test_shared_components_hurt_more_than_the_parallel_formula_says(self):
        quiet = {k: (1e12, 1.0) for k in resilience.FAILURE_PARAMS}; quiet["rack"] = (2000.0, 4.0)
        hosts = [H("h1", "R1", ("A",), ("S1",), ("C1",)), H("h2", "R1", ("A",), ("S1",), ("C1",))]
        vms = [VM("v1", 2, 4, "web", "g"), VM("v2", 2, 4, "web", "g")]
        d = tiny(hosts, vms, {"v1": "h1", "v2": "h2"}, edge=("FW1",), arrays={"S1": True}, vm_array={"v1": "S1", "v2": "S1"})
        got = 1 - resilience.availability(d, 30000, 5, quiet)["groups"]["g"]["availability"]
        independent = (4 / 2004) ** 2
        self.assertGreater(got, 100 * independent)                # both replicas share one rack, so the rack failure takes both

    def test_same_seed_same_result(self):
        d = designs.reference_design("resilient")
        a = resilience.availability(d, 300, 2); b = resilience.availability(d, 300, 2)
        self.assertEqual(a["end_to_end"]["downtime_min_per_year"], b["end_to_end"]["downtime_min_per_year"])


class DesignTests(unittest.TestCase):
    def test_reference_designs_are_valid(self):
        for k in ("basic", "segmented", "resilient"):
            d = designs.reference_design(k)
            self.assertEqual(len(d.placement), len(d.vms))
            self.assertEqual(sum(1 for v in d.vms if v.tier == "db"), 2)
        self.assertEqual(designs.reference_design("basic").default_action, "allow")
        self.assertTrue(all(len(h.feeds) == 2 for h in designs.reference_design("resilient").hosts))

    def test_design_scores_are_ordered(self):
        o = {k: evaluate.evaluate(designs.reference_design(k), 300)["overall"] for k in ("basic", "segmented", "resilient")}
        self.assertLess(o["basic"], o["segmented"]); self.assertLess(o["segmented"], o["resilient"])

    def test_resilient_design_has_no_single_point_of_failure(self):
        r = evaluate.evaluate(designs.reference_design("resilient"), 300)
        self.assertEqual(r["resilience"]["spofs"], [])
        self.assertTrue(r["resilience"]["tier"]["label"].startswith("Tier III"))
        self.assertTrue(evaluate.evaluate(designs.reference_design("basic"), 300)["resilience"]["tier"]["label"].startswith("Tier I-"))

    def test_basic_design_has_the_expected_single_points_of_failure(self):
        r = evaluate.evaluate(designs.reference_design("basic"), 300)
        self.assertEqual({s["component"].split()[0] for s in r["resilience"]["spofs"]}, {"array", "cooling", "edge", "feed", "rack", "switch"})

    def test_harden_improves_everything_technical(self):
        b = designs.reference_design("basic"); h, ch = designs.harden(b)
        rb, rh = evaluate.evaluate(b, 300), evaluate.evaluate(h, 300)
        self.assertGreater(rh["security"]["policy_score"], 99); self.assertEqual(rh["resilience"]["spofs"], [])
        self.assertGreater(rh["overall"], rb["overall"] + 30); self.assertGreaterEqual(len(ch), 10)
        self.assertEqual({v.name for v in h.vms}, {v.name for v in b.vms})

    def test_harden_does_not_touch_process_items_and_is_idempotent(self):
        h, _ = designs.harden(designs.reference_design("basic"))
        self.assertEqual(h.hardening, designs.reference_design("basic").hardening)
        again, changes = designs.harden(h)
        self.assertEqual(changes, [])

    def test_harden_leaves_the_original_alone(self):
        b = designs.reference_design("basic"); designs.harden(b)
        self.assertEqual(b.default_action, "allow"); self.assertEqual(len(b.edge), 1)


class InterfaceTests(unittest.TestCase):
    def test_cli(self):
        self.assertEqual(cli.main(["evaluate", "basic", "--years", "100"]), 0)
        self.assertEqual(cli.main(["harden", "basic", "--years", "100"]), 0)

    def test_server(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        def post(path, body):
            req = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req))
        try:
            r = post("/api/evaluate", {"kind": "resilient", "years": 100})
            bad = post("/api/evaluate", {"kind": "resilient", "years": 100, "default_action": "allow", "rules": [{"src": "any", "dst": "any", "port": "any", "action": "allow"}]})
            h = post("/api/harden", {"kind": "basic", "years": 100})
            try:
                post("/api/evaluate", {"kind": "resilient", "rules": [{"src": "internet"}]}); code = None
            except urllib.error.HTTPError as e:
                code = e.code
        finally:
            srv.shutdown(); srv.server_close()
        self.assertGreater(r["overall"], 90); self.assertEqual(bad["security"]["policy_score"], 0); self.assertLess(bad["security"]["score"], r["security"]["score"] - 50)
        self.assertGreater(h["after"]["overall"], h["before"]["overall"]); self.assertIn("mfa_admin", h["still_to_do"])
        self.assertEqual(code, 400)


if __name__ == "__main__":
    unittest.main()
