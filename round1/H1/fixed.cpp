#include <bits/stdc++.h>
using namespace std;
int main() {
    string s; cin >> s;
    vector<int> last(128, -1);
    int left = 0, best = 0;
    for (int i = 0; i < (int)s.size(); i++) {
        char c = s[i];
        if (last[c] >= left) left = last[c] + 1;
        last[c] = i;
        best = max(best, i - left + 1);
    }
    cout << best << endl;
}
