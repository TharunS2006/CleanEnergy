#include <bits/stdc++.h>
using namespace std;
int main() {
    int c, q; cin >> c >> q;
    list<pair<int,int> > lst;
    unordered_map<int, list<pair<int,int> >::iterator> pos;
    while (q--) {
        string op; cin >> op;
        if (op == "GET") {
            int k; cin >> k;
            if (!pos.count(k)) { cout << 0 << "\n"; continue; }
            cout << pos[k]->second << "\n";
        } else {
            int k, v; cin >> k >> v;
            if (pos.count(k)) { pos[k]->second = v; continue; }
            if ((int)lst.size() >= c) { pos.erase(lst.back().first); lst.pop_back(); }
            lst.push_front(make_pair(k, v));
            pos[k] = lst.begin();
        }
    }
}
