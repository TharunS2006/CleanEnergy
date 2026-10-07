#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; cin >> n;
    vector<int> a(n);
    for (auto &v : a) cin >> v;
    int total = 0;
    for (int i = 0; i < n; i++) total += a[i];
    cout << total << endl;
}
