#!/usr/bin/env python3
"""Generates round3/Qn/tests/NN.in|out from reference solutions. Run: python3 build_tests.py"""
import os, random
from collections import OrderedDict, deque
random.seed(20261009)
HERE = os.path.dirname(os.path.abspath(__file__))

def ref_lru(inp):
    lines = inp.strip().split("\n"); c, q = map(int, lines[0].split()); cache = OrderedDict(); out = []
    for ln in lines[1:1 + q]:
        p = ln.split()
        if p[0] == "GET":
            k = int(p[1])
            if k in cache: cache.move_to_end(k); out.append(str(cache[k]))
            else: out.append("-1")
        else:
            k, v = int(p[1]), int(p[2]); cache[k] = v; cache.move_to_end(k)
            if len(cache) > c: cache.popitem(last=False)
    return "\n".join(out)

def ref_knap(inp):
    d = inp.split(); n, W = int(d[0]), int(d[1]); dp = [0] * (W + 1)
    for i in range(n):
        w, v = int(d[2 + 2 * i]), int(d[3 + 2 * i])
        for c in range(W, w - 1, -1):
            if dp[c - w] + v > dp[c]: dp[c] = dp[c - w] + v
    return str(dp[W])

def ref_islands(inp):
    ls = inp.split("\n"); r, c = map(int, ls[0].split()); g = ls[1:1 + r]; seen = [bytearray(c) for _ in range(r)]; cnt = 0
    for i in range(r):
        for j in range(c):
            if g[i][j] == "1" and not seen[i][j]:
                cnt += 1; seen[i][j] = 1; st = [(i, j)]
                while st:
                    x, y = st.pop()
                    for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                        if 0 <= nx < r and 0 <= ny < c and g[nx][ny] == "1" and not seen[nx][ny]:
                            seen[nx][ny] = 1; st.append((nx, ny))
    return str(cnt)

def lru(c, ops): return f"{c} {len(ops)}\n" + "\n".join(ops) + "\n"
def knap(W, items): return f"{len(items)} {W}\n" + "".join(f"{w} {v}\n" for w, v in items)
def grid(rows): return f"{len(rows)} {len(rows[0])}\n" + "\n".join(rows) + "\n"
def rgrid(r, c, p): return grid(["".join("1" if random.random() < p else "0" for _ in range(c)) for _ in range(r)])

T = {}
big_ops = []
for _ in range(100000):
    if random.random() < 0.5: big_ops.append(f"PUT {random.randint(1, 3000)} {random.randint(1, 10**9)}")
    else: big_ops.append(f"GET {random.randint(1, 3000)}")
T["Q1"] = [
    lru(2, ["PUT 1 1", "PUT 2 2", "GET 1", "PUT 3 3", "GET 2", "GET 1"]),
    lru(1, ["PUT 1 10", "PUT 2 20", "GET 1", "GET 2"]),
    lru(2, ["GET 5", "PUT 5 50", "GET 5"]),
    lru(2, ["PUT 1 1", "PUT 2 2", "PUT 1 100", "PUT 3 3", "GET 1", "GET 2", "GET 3"]),
    lru(3, ["PUT 1 1", "PUT 2 2", "PUT 3 3", "GET 1", "PUT 4 4", "GET 2", "GET 3", "GET 1", "GET 4"]),
    lru(3, ["PUT 1 1", "PUT 2 2", "PUT 3 3", "PUT 4 4", "GET 1", "GET 2", "GET 3", "GET 4"]),
    lru(2, ["PUT 1 1", "PUT 2 2", "GET 1", "GET 1", "PUT 3 3", "GET 2", "GET 3", "GET 1"]),
    lru(5, [("PUT %d %d" % (random.randint(1, 8), random.randint(1, 99))) if random.random() < 0.5 else "GET %d" % random.randint(1, 8) for _ in range(60)]),
    lru(1000, big_ops), lru(1, big_ops[:50000]),
]
T["Q2"] = [
    knap(50, [(10, 60), (20, 100), (30, 120)]),
    knap(10, [(5, 10)]), knap(10, [(20, 99)]), knap(7, [(3, 4), (4, 5), (2, 3)]),
    knap(5, [(5, 1000000000), (5, 1000000000), (2, 7)]),
    knap(10000, [(random.randint(1, 3000), random.randint(1, 10**9)) for _ in range(500)]),
    knap(10000, [(random.randint(1, 30), random.randint(1, 10**9)) for _ in range(500)]),
    knap(100, [(random.randint(1, 40), random.randint(1, 100)) for _ in range(30)]),
    knap(1, [(1, 5), (1, 9), (2, 100)]),
    knap(10000, [(1, 10**9)] * 500),
]
big = rgrid(1000, 1000, 0.55)
chess = grid(["".join("1" if (i + j) % 2 == 0 else "0" for j in range(1000)) for i in range(1000)])
T["Q3"] = [
    grid(["11000", "11000", "00100", "00011"]),
    grid(["1"]), grid(["0"]), grid(["000", "000"]), grid(["111", "111", "111"]),
    grid(["1010101", "0101010", "1010101"]),
    grid(["101", "010", "101", "010", "101", "010", "101"]),
    grid(["1" + "0" * 9, "0" * 10, "0" * 9 + "1"]),
    rgrid(40, 60, 0.5), rgrid(300, 200, 0.6), big, chess,
    grid(["1" * 1000] * 1000),
]
REF = {"Q1": ref_lru, "Q2": ref_knap, "Q3": ref_islands}
for q, tests in T.items():
    td = os.path.join(HERE, q, "tests"); os.makedirs(td, exist_ok=True)
    for f in os.listdir(td): os.remove(os.path.join(td, f))
    for i, inp in enumerate(tests, 1):
        open(os.path.join(td, f"{i:02d}.in"), "w").write(inp)
        open(os.path.join(td, f"{i:02d}.out"), "w").write(REF[q](inp) + "\n")
    print(q, len(tests), "tests")
