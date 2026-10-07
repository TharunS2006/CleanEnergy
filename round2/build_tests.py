#!/usr/bin/env python3
"""Generates round2/Qn/tests/NN.in|out from reference solutions. Run: python3 build_tests.py"""
import heapq, os, random
random.seed(20261008)
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- reference solutions ----------
def ref_brackets(inp):
    lines = inp.split("\n"); t = int(lines[0]); out = []
    for s in lines[1:1 + t]:
        st = []; ok = True
        for c in s:
            if c in "([{": st.append(c)
            else:
                if not st or {")": "(", "]": "[", "}": "{"}[c] != st.pop(): ok = False; break
        out.append("YES" if ok and not st else "NO")
    return "\n".join(out)

def ref_dijkstra(inp):
    d = inp.split(); n, m = int(d[0]), int(d[1]); g = [[] for _ in range(n + 1)]
    for i in range(m):
        u, v, w = int(d[2 + 3 * i]), int(d[3 + 3 * i]), int(d[4 + 3 * i]); g[u].append((v, w)); g[v].append((u, w))
    INF = float("inf"); dist = [INF] * (n + 1); dist[1] = 0; pq = [(0, 1)]
    while pq:
        dd, u = heapq.heappop(pq)
        if dd > dist[u]: continue
        for v, w in g[u]:
            if dd + w < dist[v]: dist[v] = dd + w; heapq.heappush(pq, (dist[v], v))
    return " ".join(str(-1 if x == INF else x) for x in dist[1:])

def ref_topo(inp):
    d = inp.split(); n, m = int(d[0]), int(d[1]); g = [[] for _ in range(n + 1)]; indeg = [0] * (n + 1)
    for i in range(m):
        u, v = int(d[2 + 2 * i]), int(d[3 + 2 * i]); g[u].append(v); indeg[v] += 1
    q = [i for i in range(1, n + 1) if indeg[i] == 0]; heapq.heapify(q); order = []
    while q:
        u = heapq.heappop(q); order.append(u)
        for v in g[u]:
            indeg[v] -= 1
            if indeg[v] == 0: heapq.heappush(q, v)
    return " ".join(map(str, order)) if len(order) == n else "CYCLE"

def ref_edit(inp):
    s, t = inp.split(); n, m = len(s), len(t); prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (s[i - 1] != t[j - 1]))
        prev = cur
    return str(prev[m])

# ---------- test input builders ----------
def brk(lines): return f"{len(lines)}\n" + "\n".join(lines) + "\n"
def graph(n, edges): return f"{n} {len(edges)}\n" + "".join(f"{u} {v} {w}\n" for u, v, w in edges)
def dag(n, edges): return f"{n} {len(edges)}\n" + "".join(f"{u} {v}\n" for u, v in edges)

def balanced(k):
    s = []
    def rec(d):
        if d == 0: return ""
        b = random.choice(["()", "[]", "{}"]); a = random.randint(0, d - 1)
        return b[0] + rec(a) + b[1] + rec(d - 1 - a)
    return rec(k)

T = {}
T["Q1"] = [
    brk(["{[()]}", "([)]", "(("]),
    brk([")"]), brk(["]"]), brk(["("]), brk(["()[]{}"]), brk(["(()"]), brk(["{[}]"]),
    brk(["())", "([{}])", "[(])", "}{", "[]]"]),
    brk(["(" * 50000 + ")" * 50000]),
    brk(["(" * 50000 + "]" * 50000]),
    brk([balanced(30) for _ in range(20)]),
    brk([balanced(40000) , balanced(40000) + ")", "[" + balanced(30000)]),
]
chain = [(i, i + 1, 10**9) for i in range(1, 5)]
rn = 200000; redges = [(random.randint(1, rn), random.randint(1, rn), random.randint(1, 10**9)) for _ in range(rn)]
T["Q2"] = [
    graph(4, [(1, 2, 5), (2, 3, 7), (1, 3, 20)]),
    graph(1, []), graph(3, [(2, 1, 4), (3, 2, 6)]), graph(5, chain), graph(5, [(1, 2, 3), (4, 5, 1)]),
    graph(4, [(1, 2, 5), (1, 2, 2), (2, 2, 1), (2, 3, 3), (3, 4, 1), (1, 4, 10)]),
    graph(3, [(3, 2, 1), (2, 1, 1)]),
    graph(200000, [(i, i + 1, 10**9) for i in range(1, 200000)]),
    graph(rn, redges),
    graph(100000, [(1, i, random.randint(1, 10**9)) for i in range(2, 100001)] + [(random.randint(2, 100000), random.randint(2, 100000), random.randint(1, 10**9)) for _ in range(100000)]),
    graph(50, [(random.randint(1, 50), random.randint(1, 50), random.randint(1, 20)) for _ in range(120)]),
]
perm = list(range(1, 100001)); random.shuffle(perm)
bigdag = [tuple(sorted((random.randrange(100000), random.randrange(100000)))) for _ in range(100000)]
bigdag = [(perm[a], perm[b]) for a, b in bigdag if a != b]
T["Q3"] = [
    dag(4, [(1, 2), (1, 3), (3, 4)]),
    dag(3, [(1, 2), (2, 3), (3, 1)]), dag(4, [(4, 1), (3, 2)]), dag(1, []), dag(2, [(1, 1)]),
    dag(5, [(2, 3), (3, 4), (4, 2)]), dag(5, []), dag(5, [(5, 4), (4, 3), (3, 2), (2, 1)]),
    dag(6, [(6, 1), (5, 1), (3, 2), (4, 2), (1, 2)]),
    dag(100000, bigdag),
    dag(100000, [(i, i + 1) for i in range(1, 100000)] + [(100000, 1)]),
    dag(100000, [(i + 1, i) for i in range(1, 100000)]),
]
def rstr(n, a): return "".join(random.choice(a) for _ in range(n))
s1 = rstr(1500, "ACGT"); s2 = list(s1)
for _ in range(200): s2[random.randrange(1500)] = random.choice("ACGT")
T["Q4"] = ["kitten sitting\n", "a b\n", "abc abc\n", "intention execution\n", "horse ros\n", "a abcdef\n",
           "abcdef a\n", "sunday saturday\n", "zzzz aaaa\n", "abc yabd\n", "ab ba\n",
           rstr(1500, "ab") + " " + rstr(1400, "ab") + "\n", s1 + " " + "".join(s2) + "\n",
           "a" * 2000 + " " + "a" * 2000 + "\n", "a" * 2000 + " " + "b" * 2000 + "\n"]
REF = {"Q1": ref_brackets, "Q2": ref_dijkstra, "Q3": ref_topo, "Q4": ref_edit}
for q, tests in T.items():
    td = os.path.join(HERE, q, "tests"); os.makedirs(td, exist_ok=True)
    for f in os.listdir(td): os.remove(os.path.join(td, f))
    for i, inp in enumerate(tests, 1):
        open(os.path.join(td, f"{i:02d}.in"), "w").write(inp)
        open(os.path.join(td, f"{i:02d}.out"), "w").write(REF[q](inp) + "\n")
    print(q, len(tests), "tests")
