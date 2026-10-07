import sys, heapq
data = sys.stdin.read().split()
n, m = int(data[0]), int(data[1])
g = [[] for _ in range(n + 1)]
indeg = [0] * (n + 1)
for i in range(m):
    u, v = int(data[2 + 2 * i]), int(data[3 + 2 * i])
    g[u].append(v)
    indeg[v] += 1
q = [i for i in range(1, n + 1) if indeg[i] == 0]
heapq.heapify(q)
order = []
while q:
    u = heapq.heappop(q)
    order.append(u)
    for v in g[u]:
        indeg[v] -= 1
        if indeg[v] == 0:
            heapq.heappush(q, v)
print(" ".join(map(str, order)) if len(order) == n else "CYCLE")
