#include <bits/stdc++.h>
using namespace std;
int main() {
    int n, W; cin >> n >> W;
    vector<int> dp(W, 0);
    for (int i = 0; i < n; i++) {
        int v, w; cin >> v >> w;
        for (int c = w; c <= W; c++) dp[c] = max(dp[c], dp[c - w] + v);
    }
    cout << dp[W] << endl;
}
