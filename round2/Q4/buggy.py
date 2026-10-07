s, t = input().split()
n, m = len(s), len(t)
dp = [[0] * m for _ in range(n)]
for i in range(1, n + 1):
    for j in range(1, m + 1):
        cost = 1 if s[i] == t[j] else 0
        dp[i][j] = min(dp[i - 1][j] + 1, dp[i - 1][j - 1] + cost)
print(dp[n][m])
