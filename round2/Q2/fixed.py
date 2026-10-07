import heapq, sys
data = sys.stdin.read().split()
n, m = int(data[0]), int(data[1])
g = [[] for _ in range(n + 1)]
p = 2
for _ in range(m):
    u, v, w = int(data[p]), int(data[p + 1]), int(data[p + 2])
    p += 3
    g[u].append((v, w))
    g[v].append((u, w))
INF = float('inf')
dist = [INF] * (n + 1)
dist[1] = 0
pq = [(0, 1)]
while pq:
    d, u = heapq.heappop(pq)
    if d > dist[u]:
        continue
    for v, w in g[u]:
        if d + w < dist[v]:
            dist[v] = d + w
            heapq.heappush(pq, (dist[v], v))
print(" ".join(str(-1 if x == INF else x) for x in dist[1:]))
