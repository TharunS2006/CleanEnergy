# HackerRank copy-paste sheet (Round 1)
For each question: Manage Challenges → Create Challenge. Paste the statement, add each test (first = Sample), enable C++/Java/Python, paste each language's stub, set the score. Do NOT paste the fixed code.

---

## E1 — Score: 20

# E1 – Sum of Sensor Readings
**Language:** Python · **Level:** Easy · **Points:** 20

Print the sum of `n` integers. The code below has bugs; fix them (keep the original structure).

**Input:** `n`, then `n` integers
**Output:** The sum
**Constraints:** 1 <= n <= 100, |a_i| <= 1000

**Sample input**
```
3
5 10 20
```
**Sample output**
```
35
```

### Tests (first one = Sample, the rest hidden)

**Test 01**
Input:
```
3
5 10 20
```
Expected output:
```
35
```

**Test 02**
Input:
```
1
7
```
Expected output:
```
7
```

**Test 03**
Input:
```
4
-3 -4 10 2
```
Expected output:
```
5
```

**Test 04**
Input:
```
3
0 0 0
```
Expected output:
```
0
```

**Test 05**: large input, copy from `E1/tests/05.in` and `E1/tests/05.out`

**Test 06**
Input:
```
50
-757 -346 29 948 48 325 761 951 -790 810 -543 832 230 272 139 -139 604 172 121 725 496 590 573 5 538 583 201 -97 -509 -995 257 -835 -774 -412 672 -800 -80 -977 668 824 403 4 391 -357 -570 -187 -485 -288 903 -270
```
Expected output:
```
3864
```

### C++ code stub
```cpp
#include <bits/stdc++.h>
using namespace std;
int main() {
    int n; cin >> n;
    vector<int> a(n);
    for (auto &v : a) cin >> v;
    int total = 1;
    for (int i = 1; i < n; i++) total += a[i];
    cout << total << endl;
}
```

### Java code stub
```java
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt();
        int[] a = new int[n];
        for (int i = 0; i < n; i++) a[i] = sc.nextInt();
        int total = 1;
        for (int i = 1; i < n; i++) total += a[i];
        System.out.println(total);
    }
}
```

### Python code stub
```py
n = int(input())
a = list(map(int, input().split()))
total = 1
for i in range(1, n):
    total += a[i]
print(total)
```

---

## E2 — Score: 20

# E2 – Peak Voltage
**Language:** C++ · **Level:** Easy · **Points:** 20

Print the largest of `n` readings (they may be negative). The code below has bugs; fix them (keep the original structure).

**Input:** `n`, then `n` integers
**Output:** The maximum
**Constraints:** 1 <= n <= 100, |a_i| <= 10^6

**Sample input**
```
3
-5 -2 -9
```
**Sample output**
```
-2
```

### Tests (first one = Sample, the rest hidden)

**Test 01**
Input:
```
3
-5 -2 -9
```
Expected output:
```
-2
```

**Test 02**
Input:
```
1
-1
```
Expected output:
```
-1
```

**Test 03**
Input:
```
3
3 9 2
```
Expected output:
```
9
```

**Test 04**
Input:
```
4
-100 -7 -50 -8
```
Expected output:
```
-7
```

**Test 05**
Input:
```
3
0 -1 -2
```
Expected output:
```
0
```

**Test 06**
Input:
```
40
-155754 -605375 -217794 -461465 -331305 -919973 -241763 -643071 -905980 -415471 -435799 -693689 -698428 -520332 -852268 -80950 -323884 -261829 -248785 -394528 -675992 -974059 -111024 -254607 -613239 -618799 -516531 -557273 -904911 -581856 -65752 -385831 -418619 -477332 -90649 -877896 -553891 -469045 -158467 -213415
```
Expected output:
```
-65752
```

### C++ code stub
```cpp
#include <bits/stdc++.h>
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
```

### Java code stub
```java
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt();
        int mx = 0;
        for (int i = 0; i < n; i++) {
            int x = sc.nextInt();
            if (x < mx) mx = x;
        }
        System.out.println(mx);
    }
}
```

### Python code stub
```py
n = int(input())
a = list(map(int, input().split()))
mx = 0
for x in a:
    if x < mx:
        mx = x
print(mx)
```

---

## M1 — Score: 50

# M1 – Caesar Cipher
**Language:** Java · **Level:** Moderate · **Points:** 50

Shift every letter by `k` (k may be negative). Keep the case. Non-letters stay unchanged. The code below has bugs; fix them (keep the original structure).

**Input:** `k` on line 1, text on line 2
**Output:** The shifted text
**Constraints:** |k| <= 1000, text length <= 1000

**Sample input**
```
3
Hello, World!
```
**Sample output**
```
Khoor, Zruog!
```

### Tests (first one = Sample, the rest hidden)

**Test 01**
Input:
```
3
Hello, World!
```
Expected output:
```
Khoor, Zruog!
```

**Test 02**
Input:
```
-3
Khoor, Zruog!
```
Expected output:
```
Hello, World!
```

**Test 03**
Input:
```
0
IEEE 2026
```
Expected output:
```
IEEE 2026
```

**Test 04**
Input:
```
26
abcXYZ
```
Expected output:
```
abcXYZ
```

**Test 05**
Input:
```
-1
abcxyz ABCXYZ
```
Expected output:
```
zabwxy ZABWXY
```

**Test 06**
Input:
```
29
The Quick Brown Fox.
```
Expected output:
```
Wkh Txlfn Eurzq Ira.
```

**Test 07**
Input:
```
-1000
Hello, World!
```
Expected output:
```
Vszzc, Kcfzr!
```

**Test 08**
Input:
```
1000
zZaA
```
Expected output:
```
lLmM
```

**Test 09**
Input:
```
-27
abc
```
Expected output:
```
zab
```

**Test 10**
Input:
```
13
Uryyb, Jbeyq!
```
Expected output:
```
Hello, World!
```

### C++ code stub
```cpp
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
```

### Java code stub
```java
import java.util.*;
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
```

### Python code stub
```py
k = int(input())
s = input()
k = k % 26
res = []
for c in s:
    if c.islower():
        res.append(chr((ord(c) - ord('a') + k) % 26))
    elif c.isupper():
        res.append(chr(ord('A') + (ord(c) - ord('a') + k) % 26))
    else:
        res.append(c)
print("".join(res))
```

---

## M2 — Score: 50

# M2 – First Occurrence
**Language:** C++ · **Level:** Moderate · **Points:** 50

Given a sorted array, print the 0-based index of the **first** occurrence of `t`, or `-1`. The code below has bugs; fix them (keep the original structure).

**Input:** `n t`, then `n` sorted integers
**Output:** The index or -1
**Constraints:** 1 <= n <= 10^5

**Sample input**
```
6 3
1 3 3 3 5 7
```
**Sample output**
```
1
```

### Tests (first one = Sample, the rest hidden)

**Test 01**
Input:
```
6 3
1 3 3 3 5 7
```
Expected output:
```
1
```

**Test 02**
Input:
```
1 5
5
```
Expected output:
```
0
```

**Test 03**
Input:
```
1 4
5
```
Expected output:
```
-1
```

**Test 04**
Input:
```
5 2
1 2 2 2 2
```
Expected output:
```
1
```

**Test 05**
Input:
```
5 1
1 1 1 1 1
```
Expected output:
```
0
```

**Test 06**
Input:
```
4 9
1 2 3 4
```
Expected output:
```
-1
```

**Test 07**
Input:
```
4 0
1 2 3 4
```
Expected output:
```
-1
```

**Test 08**
Input:
```
7 7
1 2 3 4 5 6 7
```
Expected output:
```
6
```

**Test 09**
Input:
```
8 4
4 4 4 4 4 4 4 4
```
Expected output:
```
0
```

**Test 10**
Input:
```
6 -2
-5 -2 -2 0 3 3
```
Expected output:
```
1
```

**Test 11**: large input, copy from `M2/tests/11.in` and `M2/tests/11.out`

### C++ code stub
```cpp
#include <bits/stdc++.h>
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
```

### Java code stub
```java
import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt(), t = sc.nextInt();
        int[] a = new int[n];
        for (int i = 0; i < n; i++) a[i] = sc.nextInt();
        int lo = 0, hi = n, ans = -1;
        while (lo < hi) {
            int mid = lo + (hi - lo) / 2;
            if (a[mid] == t) { ans = mid; lo = mid + 1; }
            else if (a[mid] < t) lo = mid + 1;
            else hi = mid - 1;
        }
        System.out.println(ans);
    }
}
```

### Python code stub
```py
n, t = map(int, input().split())
a = list(map(int, input().split()))
lo, hi, ans = 0, n, -1
while lo < hi:
    mid = lo + (hi - lo) // 2
    if a[mid] == t:
        ans = mid
        lo = mid + 1
    elif a[mid] < t:
        lo = mid + 1
    else:
        hi = mid - 1
print(ans)
```

---

## H1 — Score: 100

# H1 – Longest Unique-Character Key
**Language:** Java · **Level:** Hard · **Points:** 100

Print the length of the longest substring with no repeated character. The code below has bugs; fix them (keep the original structure).

**Input:** one string of printable ASCII without spaces
**Output:** The length
**Constraints:** 1 <= length <= 10^5

**Sample input**
```
abcabcbb
```
**Sample output**
```
3
```

### Tests (first one = Sample, the rest hidden)

**Test 01**
Input:
```
abcabcbb
```
Expected output:
```
3
```

**Test 02**
Input:
```
abba
```
Expected output:
```
2
```

**Test 03**
Input:
```
bbbbb
```
Expected output:
```
1
```

**Test 04**
Input:
```
pwwkew
```
Expected output:
```
3
```

**Test 05**
Input:
```
a
```
Expected output:
```
1
```

**Test 06**
Input:
```
abcdef
```
Expected output:
```
6
```

**Test 07**
Input:
```
dvdf
```
Expected output:
```
3
```

**Test 08**
Input:
```
tmmzuxt
```
Expected output:
```
5
```

**Test 09**
Input:
```
aab
```
Expected output:
```
2
```

**Test 10**
Input:
```
abcb
```
Expected output:
```
3
```

**Test 11**
Input:
```
!@#!@#$%
```
Expected output:
```
5
```

**Test 12**: large input, copy from `H1/tests/12.in` and `H1/tests/12.out`

**Test 13**: large input, copy from `H1/tests/13.in` and `H1/tests/13.out`

**Test 14**: large input, copy from `H1/tests/14.in` and `H1/tests/14.out`

### C++ code stub
```cpp
#include <bits/stdc++.h>
using namespace std;
int main() {
    string s; cin >> s;
    vector<int> last(128, 0);
    int left = 0, best = 0;
    for (int i = 0; i < (int)s.size(); i++) {
        char c = s[i];
        if (last[c] >= 0) left = last[c] + 1;
        last[c] = i;
        best = max(best, i - left);
    }
    cout << best << endl;
}
```

### Java code stub
```java
import java.util.*;
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
```

### Python code stub
```py
s = input().strip()
last = {}
left = best = 0
for i, c in enumerate(s):
    if c in last:
        left = last[c] + 1
    last[c] = i
    best = max(best, i - left)
print(best)
```
