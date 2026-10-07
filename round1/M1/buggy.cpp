#include <bits/stdc++.h>
using namespace std;
int main() {
    int k; string s;
    cin >> k; cin.ignore();
    getline(cin, s);
    k = k % 26;
    string out;
    for (char c : s) {
        if (islower(c)) out += (char)((c - 'a' + k) % 26);
        else if (isupper(c)) out += (char)('A' + (c - 'a' + k) % 26);
        else out += c;
    }
    cout << out << endl;
}
