#include <bits/stdc++.h>
using namespace std;
bool ok(const string &s) {
    stack<char> st;
    for (char c : s) {
        if (c == '(' || c == '[' || c == '{') st.push(c);
        else {
            if (st.empty()) return false;
            char top = st.top(); st.pop();
            if ((c == ')' && top != '(') || (c == ']' && top != '[') || (c == '}' && top != '{'))
                return false;
        }
    }
    return st.empty();
}
int main() {
    int t; cin >> t;
    while (t--) { string s; cin >> s; cout << (ok(s) ? "YES" : "NO") << "\n"; }
}
