#!/usr/bin/env python3
"""Generates round1/<ID>/ (statement, buggy, fixed, tests) and validates them.
Run: python3 build.py   (needs g++, javac/java, python3)"""
import os, random, subprocess, sys, tempfile, shutil

random.seed(2026)
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- reference solutions (used only to produce expected outputs) ----------
def ref_e1(inp):
    t = inp.split(); n = int(t[0]); return str(sum(map(int, t[1:1+n])))
def ref_e2(inp):
    t = inp.split(); n = int(t[0]); return str(max(map(int, t[1:1+n])))
def ref_m1(inp):
    k, s = inp.split("\n", 1); k = int(k); s = s.rstrip("\n"); out = []
    for c in s:
        if c.islower() and c.isascii(): out.append(chr((ord(c)-97+k) % 26 + 97))
        elif c.isupper() and c.isascii(): out.append(chr((ord(c)-65+k) % 26 + 65))
        else: out.append(c)
    return "".join(out)
def ref_m2(inp):
    t = inp.split(); n, x = int(t[0]), int(t[1]); a = list(map(int, t[2:2+n]))
    return str(a.index(x) if x in a else -1)
def ref_h1(inp):
    s = inp.strip(); last = {}; left = best = 0
    for i, c in enumerate(s):
        if c in last and last[c] >= left: left = last[c] + 1
        last[c] = i; best = max(best, i - left + 1)
    return str(best)

# ---------- test inputs ----------
def arr(a): return f"{len(a)}\n{' '.join(map(str, a))}\n"
T = {}
T["E1"] = [arr([5,10,20]), arr([7]), arr([-3,-4,10,2]), arr([0,0,0]), arr([1000]*100),
           arr([random.randint(-1000,1000) for _ in range(50)])]
T["E2"] = [arr([-5,-2,-9]), arr([-1]), arr([3,9,2]), arr([-100,-7,-50,-8]), arr([0,-1,-2]),
           arr([random.randint(-10**6,-1) for _ in range(40)])]
T["M1"] = [f"3\nHello, World!\n", "-3\nKhoor, Zruog!\n", "0\nIEEE 2026\n", "26\nabcXYZ\n",
           "-1\nabcxyz ABCXYZ\n", "29\nThe Quick Brown Fox.\n", "-1000\nHello, World!\n", "1000\nzZaA\n",
           "-27\nabc\n", "13\nUryyb, Jbeyq!\n"]
T["M2"] = ["6 3\n1 3 3 3 5 7\n", "1 5\n5\n", "1 4\n5\n", "5 2\n1 2 2 2 2\n", "5 1\n1 1 1 1 1\n",
           "4 9\n1 2 3 4\n", "4 0\n1 2 3 4\n", "7 7\n1 2 3 4 5 6 7\n", "8 4\n4 4 4 4 4 4 4 4\n",
           "6 -2\n-5 -2 -2 0 3 3\n"]
big = sorted(random.randint(1, 50) for _ in range(5000))
T["M2"].append(f"5000 {big[2500]}\n{' '.join(map(str, big))}\n")
def rs(n, alpha): return "".join(random.choice(alpha) for _ in range(n))
T["H1"] = ["abcabcbb\n", "abba\n", "bbbbb\n", "pwwkew\n", "a\n", "abcdef\n", "dvdf\n", "tmmzuxt\n",
           "aab\n", "abcb\n", "!@#!@#$%\n", rs(1000, "abcdefgh") + "\n", "".join(chr(33 + i % 94) for i in range(100000)) + "\n",
           "a" * 100000 + "\n"]

# ---------- code ----------
CODE = {}
CODE["E1"] = ("py",
"""n = int(input())
a = list(map(int, input().split()))
total = 1
for i in range(1, n):
    total += a[i]
print(total)
""",
"""n = int(input())
a = list(map(int, input().split()))
total = 0
for i in range(n):
    total += a[i]
print(total)
""")
CODE["E2"] = ("cpp",
"""#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; cin >> n;
    int mx = 0;
    for (int i = 0; i < n; i++) {
        int x; cin >> x;
        if (x < mx) mx = x;
    }
    cout << mx << endl;
}
""",
"""#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; cin >> n;
    int mx = INT_MIN;
    for (int i = 0; i < n; i++) {
        int x; cin >> x;
        if (x > mx) mx = x;
    }
    cout << mx << endl;
}
""")
CODE["M1"] = ("java",
"""import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int k = Integer.parseInt(sc.nextLine().trim());
        String s = sc.nextLine();
        k = k % 26;
        StringBuilder sb = new StringBuilder();
        for (char c : s.toCharArray()) {
            if (Character.isLowerCase(c))
                sb.append((char) ((c - 'a' + k) % 26));
            else if (Character.isUpperCase(c))
                sb.append((char) ('A' + (c - 'a' + k) % 26));
            else
                sb.append(c);
        }
        System.out.println(sb);
    }
}
""",
"""import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int k = Integer.parseInt(sc.nextLine().trim());
        String s = sc.nextLine();
        k = ((k % 26) + 26) % 26;
        StringBuilder sb = new StringBuilder();
        for (char c : s.toCharArray()) {
            if (Character.isLowerCase(c))
                sb.append((char) ('a' + (c - 'a' + k) % 26));
            else if (Character.isUpperCase(c))
                sb.append((char) ('A' + (c - 'A' + k) % 26));
            else
                sb.append(c);
        }
        System.out.println(sb);
    }
}
""")
CODE["M2"] = ("cpp",
"""#include <bits/stdc++.h>
using namespace std;
int main() {
    int n, t; cin >> n >> t;
    vector<int> a(n);
    for (auto &v : a) cin >> v;
    int lo = 0, hi = n, ans = -1;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] == t) { ans = mid; lo = mid + 1; }
        else if (a[mid] < t) lo = mid + 1;
        else hi = mid - 1;
    }
    cout << ans << endl;
}
""",
"""#include <bits/stdc++.h>
using namespace std;
int main() {
    int n, t; cin >> n >> t;
    vector<int> a(n);
    for (auto &v : a) cin >> v;
    int lo = 0, hi = n - 1, ans = -1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] == t) { ans = mid; hi = mid - 1; }
        else if (a[mid] < t) lo = mid + 1;
        else hi = mid - 1;
    }
    cout << ans << endl;
}
""")
CODE["H1"] = ("java",
"""import java.util.*;
public class Main {
    public static void main(String[] args) {
        String s = new Scanner(System.in).next();
        int[] last = new int[128];
        int left = 0, best = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (last[c] >= 0) left = last[c] + 1;
            last[c] = i;
            best = Math.max(best, i - left);
        }
        System.out.println(best);
    }
}
""",
"""import java.util.*;
public class Main {
    public static void main(String[] args) {
        String s = new Scanner(System.in).next();
        int[] last = new int[128];
        Arrays.fill(last, -1);
        int left = 0, best = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (last[c] >= left) left = last[c] + 1;
            last[c] = i;
            best = Math.max(best, i - left + 1);
        }
        System.out.println(best);
    }
}
""")
REF = dict(E1=ref_e1, E2=ref_e2, M1=ref_m1, M2=ref_m2, H1=ref_h1)

META = {
 "E1": ("Sum of Sensor Readings", "Python", "Easy", 20, "Print the sum of `n` integers.",
        "`n`, then `n` integers", "The sum", "1 <= n <= 100, |a_i| <= 1000", "3\n5 10 20\n", "35"),
 "E2": ("Peak Voltage", "C++", "Easy", 20, "Print the largest of `n` readings (they may be negative).",
        "`n`, then `n` integers", "The maximum", "1 <= n <= 100, |a_i| <= 10^6", "3\n-5 -2 -9\n", "-2"),
 "M1": ("Caesar Cipher", "Java", "Moderate", 50,
        "Shift every letter by `k` (k may be negative). Keep the case. Non-letters stay unchanged.",
        "`k` on line 1, text on line 2", "The shifted text", "|k| <= 1000, text length <= 1000",
        "3\nHello, World!\n", "Khoor, Zruog!"),
 "M2": ("First Occurrence", "C++", "Moderate", 50,
        "Given a sorted array, print the 0-based index of the **first** occurrence of `t`, or `-1`.",
        "`n t`, then `n` sorted integers", "The index or -1", "1 <= n <= 10^5", "6 3\n1 3 3 3 5 7\n", "1"),
 "H1": ("Longest Unique-Character Key", "Java", "Hard", 100,
        "Print the length of the longest substring with no repeated character.",
        "one string of printable ASCII without spaces", "The length", "1 <= length <= 10^5",
        "abcabcbb\n", "3"),
}
EXT = {"py": "py", "cpp": "cpp", "java": "java"}

def run_cmd(lang, d, which):
    if lang == "py": return ["python3", os.path.join(d, f"{which}.py")]
    if lang == "cpp":
        exe = os.path.join(tmp, f"{d.split(os.sep)[-1]}_{which}")
        subprocess.run(["g++", "-O2", "-o", exe, os.path.join(d, f"{which}.cpp")], check=True)
        return [exe]
    jd = os.path.join(tmp, f"{d.split(os.sep)[-1]}_{which}"); os.makedirs(jd, exist_ok=True)
    shutil.copy(os.path.join(d, f"{which}.java"), os.path.join(jd, "Main.java"))
    subprocess.run(["javac", "-d", jd, os.path.join(jd, "Main.java")], check=True)
    return ["java", "-cp", jd, "Main"]

def passes(cmd, tdir, names):
    res = []
    for nm in names:
        inp = open(os.path.join(tdir, nm + ".in")).read()
        exp = open(os.path.join(tdir, nm + ".out")).read().strip()
        try:
            p = subprocess.run(cmd, input=inp, capture_output=True, text=True, timeout=10)
            res.append(p.returncode == 0 and p.stdout.strip() == exp)
        except subprocess.TimeoutExpired:
            res.append(False)
    return res

tmp = tempfile.mkdtemp()
ok = True
for qid, (name, lang, lvl, pts, stmt, inf, outf, cons, si, so) in META.items():
    d = os.path.join(HERE, qid); td = os.path.join(d, "tests"); os.makedirs(td, exist_ok=True)
    ext, buggy, fixed = CODE[qid]
    open(os.path.join(d, f"buggy.{ext}"), "w").write(buggy)
    open(os.path.join(d, f"fixed.{ext}"), "w").write(fixed)
    names = []
    for i, inp in enumerate(T[qid], 1):
        nm = f"{i:02d}"; names.append(nm)
        open(os.path.join(td, nm + ".in"), "w").write(inp)
        open(os.path.join(td, nm + ".out"), "w").write(REF[qid](inp) + "\n")
    open(os.path.join(d, "statement.md"), "w").write(
f"""# {qid} – {name}
**Language:** {lang} · **Level:** {lvl} · **Points:** {pts}

{stmt} The code below has bugs; fix them (keep the original structure).

**Input:** {inf}
**Output:** {outf}
**Constraints:** {cons}

**Sample input**
```
{si}```
**Sample output**
```
{so}
```
""")
    bres = passes(run_cmd(ext, d, "buggy"), td, names)
    fres = passes(run_cmd(ext, d, "fixed"), td, names)
    good = all(fres) and not all(bres)
    ok &= good
    print(f"{qid} {name:30s} tests={len(names):2d} fixed_pass={sum(fres)}/{len(fres)} "
          f"buggy_pass={sum(bres)}/{len(bres)} {'OK' if good else 'PROBLEM'}")
shutil.rmtree(tmp)
sys.exit(0 if ok else 1)
