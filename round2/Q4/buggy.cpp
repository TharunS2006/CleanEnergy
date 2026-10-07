#include <bits/stdc++.h>
using namespace std;
int main() {
    string s, t; cin >> s >> t;
    int n = s.size(), m = t.size();
    vector<vector<int> > dp(n, vector<int>(m, 0));
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= m; j++) {
            int cost = (s[i] == t[j]) ? 1 : 0;
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i - 1][j - 1] + cost);
        }
    cout << dp[n][m] << endl;
}
