"""Measurements used in Chapter 6: automaton sizes, speed against Python's re, and agreement."""
import json, random, re, statistics, time
from urllib.parse import urlparse
from urlvalidator import validate, machines, compile_regex, grammar
from urlvalidator.cases import CASES

out = {}
# 1. automaton sizes per grammar piece
sizes = {}
for name, pat in grammar.PARTS.items():
    t = time.perf_counter(); n, d, m = compile_regex(pat); dt = time.perf_counter() - t
    sizes[name] = {"nfa": n.size, "dfa": d.size, "min": m.size, "classes": m.n_classes, "ms": round(dt * 1000, 1)}
out["sizes"] = sizes
n, d, m = machines()
out["transitions_live"] = m.transition_count()

# 2. accuracy of three approaches on the labelled cases
def by_urlparse(u):
    p = urlparse(u); return bool(p.scheme and p.netloc)
rx = re.compile(grammar.URL)
acc = {"dfa": 0, "re": 0, "urlparse": 0}
rows = []
for u, expect, why in CASES:
    a, b, c = validate(u).valid, rx.fullmatch(u) is not None, by_urlparse(u)
    acc["dfa"] += a == expect; acc["re"] += b == expect; acc["urlparse"] += c == expect
    rows.append((u, expect, a, b, c, why))
out["accuracy"] = {k: v for k, v in acc.items()}; out["n_cases"] = len(CASES)
out["urlparse_false_accepts"] = [r[0] for r in rows if r[4] and not r[1]]
out["cases"] = rows

# 3. throughput: validate() building a result vs the bare DFA loop vs re.fullmatch, on the 35 cases repeated
urls = [c[0] for c in CASES] * 200
def timeit(fn, reps=3):
    best = 1e9
    for _ in range(reps):
        t = time.perf_counter()
        for u in urls: fn(u)
        best = min(best, time.perf_counter() - t)
    return len(urls) / best
out["throughput"] = {"dfa_accepts": round(timeit(m.accepts)), "validate_full": round(timeit(validate)),
                     "re_fullmatch": round(timeit(rx.fullmatch)), "urlparse": round(timeit(by_urlparse))}

# 4. running time against input length (valid URLs with a growing path), best of 5, microseconds
scal = []
for L in (10, 100, 1000, 10000, 100000):
    u = "http://example.com/" + "a" * L
    ts = []
    for _ in range(5):
        t = time.perf_counter(); m.accepts(u); ts.append(time.perf_counter() - t)
    scal.append((len(u), round(min(ts) * 1e6, 1)))
out["scaling"] = scal

# 5. build cost
ts = []
for _ in range(5):
    t = time.perf_counter(); compile_regex(grammar.URL); ts.append(time.perf_counter() - t)
out["build_ms"] = round(statistics.median(ts) * 1000, 1)

# 6. effect of the label-length bound on the size of the automaton
grow = []
for k in (2, 8, 16, 32, 63):
    pat = grammar.URL.replace("{0,61}", "{0," + str(k - 2) + "}").replace("{2,63}", "{2," + str(k) + "}")
    nn, dd, mm = compile_regex(pat); grow.append((k, nn.size, dd.size, mm.size))
out["label_growth"] = grow
json.dump(out, open("bench_results.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "cases"}, indent=1))
