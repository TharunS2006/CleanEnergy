#include <bits/stdc++.h>
using namespace std;
int main() {
    int n, m; scanf("%d %d", &n, &m);
    vector<vector<int> > g(n + 1);
    vector<int> indeg(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int u, v; scanf("%d %d", &u, &v);
        g[u].push_back(v);
        indeg[v]++;
    }
    stack<int> q;
    for (int i = 1; i <= n; i++) if (indeg[i] == 0) q.push(i);
    vector<int> order;
    while (!q.empty()) {
        int u = q.top(); q.pop();
        order.push_back(u);
        for (size_t k = 0; k < g[u].size(); k++) {
            int v = g[u][k];
            if (--indeg[v] == 0) q.push(v);
        }
    }
    for (size_t i = 0; i < order.size(); i++) printf("%d%c", order[i], i + 1 == order.size() ? '\n' : ' ');
}
