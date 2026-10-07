n, W = map(int, input().split())
items = [tuple(map(int, input().split())) for _ in range(n)]
dp = [0] * W
for v, w in items:
    for c in range(w, W + 1):
        dp[c] = max(dp[c], dp[c - w] + v)
print(dp[W])
