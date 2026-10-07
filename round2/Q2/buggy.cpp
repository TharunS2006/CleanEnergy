#include <bits/stdc++.h>
using namespace std;
int main() {
    int n, m; scanf("%d %d", &n, &m);
    vector<vector<pair<int,int> > > g(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v, w; scanf("%d %d %d", &u, &v, &w);
        g[u].push_back(make_pair(v, w));
    }
    const int INF = INT_MAX;
    vector<int> dist(n + 1, INF);
    priority_queue<pair<int,int> > pq;
    dist[1] = 0; pq.push(make_pair(0, 1));
    while (!pq.empty()) {
        int d = pq.top().first, u = pq.top().second; pq.pop();
        for (size_t k = 0; k < g[u].size(); k++) {
            int v = g[u][k].first, w = g[u][k].second;
            if (d + w < dist[v]) { dist[v] = d + w; pq.push(make_pair(dist[v], v)); }
        }
    }
    for (int i = 1; i <= n; i++) cout << (dist[i] == INF ? -1 : dist[i]) << " \n"[i == n];
}
