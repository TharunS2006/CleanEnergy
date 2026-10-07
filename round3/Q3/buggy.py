from collections import deque
r, c = map(int, input().split())
g = [input().strip() for _ in range(r)]
vis = [[False] * c for _ in range(r)]
dx, dy = [1, -1, 0, 0], [0, 0, 1, 1]
cnt = 0
for i in range(r):
    for j in range(r):
        if g[i][j] == '1' and not vis[i][j]:
            cnt += 1
            q = deque([(i, j)])
            vis[i][j] = True
            while q:
                x, y = q.popleft()
                for d in range(4):
                    nx, ny = x + dx[d], y + dy[d]
                    if nx >= 0 and ny >= 0 and nx <= r and ny < c and g[nx][ny] == '1' and not vis[nx][ny]:
                        vis[nx][ny] = True
                        q.append((nx, ny))
print(cnt)
