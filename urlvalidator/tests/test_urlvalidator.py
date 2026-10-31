import json, random, re, threading, unittest, urllib.request
from http.server import ThreadingHTTPServer

from urlvalidator import validate, machines, compile_regex, equivalent
from urlvalidator import grammar
from urlvalidator.automata import Parser, thompson, subset_construction, minimise, RegexError
from urlvalidator.cases import CASES
from urlvalidator import cli, server


def dfa_for(pat): return compile_regex(pat)[2]


class AutomataTests(unittest.TestCase):
    def test_classic_example_has_four_live_states(self):            # (a|b)*abb: textbook minimal DFA has 4 states + sink
        n, d, m = compile_regex("(a|b)*abb")
        self.assertEqual((m.size, len(m.dead_states())), (5, 1))
        self.assertTrue(m.accepts("abb") and m.accepts("babb") and not m.accepts("ab") and not m.accepts("abba"))

    def test_subset_and_minimal_dfa_are_equivalent(self):
        n, d, m = machines()
        self.assertTrue(equivalent(d, m))
        self.assertLess(m.size, d.size)

    def test_minimising_twice_changes_nothing(self):
        m = machines()[2]
        self.assertEqual(minimise(m).size, m.size)

    def test_parser_rejects_bad_patterns(self):
        for bad in ("(ab", "a)", "[ab", "*a"):
            with self.assertRaises((RegexError, ValueError, IndexError)):
                Parser(bad).parse()

    def test_counted_repetition(self):
        m = dfa_for("a{2,4}")
        self.assertEqual([m.accepts("a" * k) for k in range(6)], [False, False, True, True, True, False])

    def test_non_ascii_never_accepted(self):
        self.assertFalse(dfa_for("[a-z]+").accepts("abcé"))

    def test_equivalence_detects_difference(self):
        self.assertFalse(equivalent(dfa_for("a*"), dfa_for("a+")))
        self.assertTrue(equivalent(dfa_for("(a|b)*"), dfa_for("(a*b*)*")))


class NumericRangeTests(unittest.TestCase):
    """Numbers up to a fixed bound are a regular language, so the automaton itself enforces the ranges."""
    def test_octet_matches_0_to_255_exactly(self):
        m = dfa_for(grammar.OCTET)
        for n in range(0, 1000):
            self.assertEqual(m.accepts(str(n)), n <= 255, n)
        self.assertFalse(m.accepts("01") or m.accepts("007"))

    def test_port_matches_1_to_65535_exactly(self):
        m = dfa_for(grammar.PORT_NUMBER)
        for n in range(0, 70000):
            self.assertEqual(m.accepts(str(n)), 1 <= n <= 65535, n)

    def test_label_length_limit_is_63(self):
        m = dfa_for(grammar.LABEL)
        self.assertTrue(m.accepts("a" * 63) and not m.accepts("a" * 64))
        self.assertTrue(m.accepts("a-b") and not m.accepts("-ab") and not m.accepts("ab-"))


class ValidatorTests(unittest.TestCase):
    def test_all_demonstration_cases(self):
        for url, expect, why in CASES:
            self.assertEqual(validate(url).valid, expect, f"{url}  ({why})")

    def test_error_position_and_expectation(self):
        r = validate("http://exa mple.com")
        self.assertEqual((r.status, r.position, r.char), ("invalid", 10, " "))
        self.assertIn("-", r.expected)

    def test_incomplete_input(self):
        r = validate("http://")
        self.assertEqual((r.status, r.position), ("incomplete", 7))
        self.assertTrue(r.expected)

    def test_ipv4_out_of_range_message(self):
        r = validate("http://10.300.1.1/")
        self.assertFalse(r.valid)
        self.assertIn("300", r.message)

    def test_components(self):
        p = validate("HTTPS://Example.com:8443/a/b?x=1&y=2#top").parts
        self.assertEqual((p["scheme"], p["host"], p["port"], p["path"], p["query"], p["fragment"]),
                         ("https", "Example.com", "8443", "/a/b", "x=1&y=2", "top"))
        self.assertEqual(validate("http://localhost").parts["host_type"], "localhost")
        self.assertEqual(validate("http://10.0.0.1").parts["host_type"], "ipv4")

    def test_trace_has_one_row_per_character(self):
        r = validate("http://a.io", trace=True)
        self.assertEqual(len(r.trace), len("http://a.io"))
        self.assertEqual(r.trace[0][3], "scheme")

    def test_phase_labels_follow_the_latest_delimiter(self):
        r = validate("http://a.io:80/p/q?x=1/2#f?g", trace=True)
        phases = {c: p for _, c, _, p in r.trace}
        self.assertEqual([phases["h"], phases["a"], phases["8"], phases["p"], phases["x"], phases["f"]],
                         ["scheme", "host", "port", "path", "query", "fragment"])
        self.assertIn("query", validate("http://example.com/?q=a b").message)

    def test_empty_string_is_incomplete(self):
        self.assertEqual(validate("").status, "incomplete")


class DifferentialTests(unittest.TestCase):
    """The automaton and Python's `re` (given the very same pattern) must agree on every string we throw at them."""
    def test_agrees_with_re_on_mutations(self):
        rx = re.compile(grammar.URL)
        rng = random.Random(7)
        seeds = [c[0] for c in CASES if c[1]]
        alphabet = "abcXYZ019-._~:/?#[]@!$&'()*+,;=% é"
        checked = 0
        for _ in range(3000):
            s = list(rng.choice(seeds))
            for _ in range(rng.randint(0, 3)):
                op, i = rng.choice("dis"), rng.randrange(len(s) + 1)
                if op == "d" and s: s.pop(min(i, len(s) - 1))
                elif op == "i": s.insert(i, rng.choice(alphabet))
                elif s: s[min(i, len(s) - 1)] = rng.choice(alphabet)
            t = "".join(s)
            self.assertEqual(validate(t).valid, rx.fullmatch(t) is not None, t)
            checked += 1
        self.assertEqual(checked, 3000)


class InterfaceTests(unittest.TestCase):
    def test_cli_exit_codes(self):
        self.assertEqual(cli.main(["https://example.com"]), 0)
        self.assertEqual(cli.main(["nope"]), 1)

    def test_server_json(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        try:
            ok = json.load(urllib.request.urlopen(base + "/api/validate?url=https%3A%2F%2Fexample.com%2Fx"))
            bad = json.load(urllib.request.urlopen(base + "/api/validate?url=http%3A%2F%2Fa%20b.com"))
            info = json.load(urllib.request.urlopen(base + "/api/info"))
            req = urllib.request.Request(base + "/api/batch", json.dumps({"urls": ["http://a.io", "x"]}).encode(), {"Content-Type": "application/json"})
            batch = json.load(urllib.request.urlopen(req))
        finally:
            srv.shutdown()
        self.assertTrue(ok["valid"] and not bad["valid"])
        self.assertEqual(bad["position"], 8)
        self.assertEqual(info["minimal"], machines()[2].size)
        self.assertEqual([b["valid"] for b in batch], [True, False])


if __name__ == "__main__":
    unittest.main()
