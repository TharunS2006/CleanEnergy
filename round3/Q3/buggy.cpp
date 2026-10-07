#include <bits/stdc++.h>
using namespace std;
int main() {
    int r, c; cin >> r >> c;
    vector<string> g(r);
    for (auto &s : g) cin >> s;
    vector<vector<bool> > vis(r, vector<bool>(c, false));
    int dx[] = {1, -1, 0, 0}, dy[] = {0, 0, 1, 1};
    int cnt = 0;
    for (int i = 0; i < r; i++)
        for (int j = 0; j < r; j++)
            if (g[i][j] == '1' && !vis[i][j]) {
                cnt++;
                queue<pair<int,int> > q;
                q.push(make_pair(i, j));
                vis[i][j] = true;
                while (!q.empty()) {
                    int x = q.front().first, y = q.front().second; q.pop();
                    for (int d = 0; d < 4; d++) {
                        int nx = x + dx[d], ny = y + dy[d];
                        if (nx >= 0 && ny >= 0 && nx <= r && ny < c && g[nx][ny] == '1' && !vis[nx][ny]) {
                            vis[nx][ny] = true;
                            q.push(make_pair(nx, ny));
                        }
                    }
                }
            }
    cout << cnt << endl;
}
