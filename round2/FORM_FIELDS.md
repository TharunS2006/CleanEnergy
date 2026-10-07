# HackerRank "Create Challenge" values – Round 2 (Details page)

Create these in a NEW private contest for the top 10. Languages: C++, Java, Python 3. Paste each language's buggy.* as its stub (Languages tab).
Tags for all: debugging, round2

---
## Q1 (Score 50)
**Challenge Name:** R2-Q1 - Balanced Brackets
**Description:** Fix the buggy program that checks whether bracket strings are balanced.
**Problem Statement:**
For each of the `t` strings made only of `()[]{}`, print `YES` if it is balanced, otherwise `NO`. The given program contains bugs. Fix them so it gives the correct output for all test cases. Keep the original structure of the code; fully rewritten solutions may be disqualified.
**Input Format:**
The first line contains `t`.

Each of the next `t` lines contains one non-empty string.
**Constraints:**
- `1 <= t <= 100`
- Each string has length at most `10^5`
**Output Format:** For each string print `YES` or `NO` on its own line.
**Sample:** input `3` / `{[()]}` / `([)]` / `((`  →  `YES` / `NO` / `NO`

---
## Q2 (Score 100)
**Challenge Name:** R2-Q2 - Shortest Network Latency
**Description:** Fix the buggy Dijkstra program that finds shortest latencies from router 1.
**Problem Statement:**
An **undirected** network has `n` routers and `m` links with latencies. Print the shortest latency from router 1 to every router (`-1` if it cannot be reached). The given program contains bugs. Fix them so it gives the correct output for all test cases. Keep the original structure of the code; fully rewritten solutions may be disqualified.
**Input Format:**
The first line contains `n` and `m`.

Each of the next `m` lines contains `u v w`, a link between routers `u` and `v` with latency `w`.
**Constraints:**
- `1 <= n, m <= 2 * 10^5`
- `1 <= w <= 10^9`
- Links may repeat, and a link may connect a router to itself.
**Output Format:** `n` space-separated integers: the shortest latency to routers 1 to n.
**Sample:** input `4 3` / `1 2 5` / `2 3 7` / `1 3 20` → `0 5 12 -1`

---
## Q3 (Score 100)
**Challenge Name:** R2-Q3 - Course Scheduler
**Description:** Fix the buggy topological sort that prints the lexicographically smallest course order.
**Problem Statement:**
There are `n` courses and `m` rules `u v` meaning course `u` must be taken before course `v`. Print the **lexicographically smallest** valid order, or `CYCLE` if no valid order exists. The given program contains bugs. Fix them so it gives the correct output for all test cases. Keep the original structure of the code; fully rewritten solutions may be disqualified.
**Input Format:**
The first line contains `n` and `m`.

Each of the next `m` lines contains `u v`.
**Constraints:**
- `1 <= n <= 10^5`
- `0 <= m <= 10^5`
**Output Format:** The order as space-separated integers, or `CYCLE`.
**Sample:** input `4 3` / `1 2` / `1 3` / `3 4` → `1 2 3 4`

---
## Q4 (Score 150)
**Challenge Name:** R2-Q4 - Edit Distance
**Description:** Fix the buggy dynamic programming program that computes edit distance.
**Problem Statement:**
Print the minimum number of insertions, deletions and substitutions needed to turn string `s` into string `t`. The given program contains bugs. Fix them so it gives the correct output for all test cases. Keep the original structure of the code; fully rewritten solutions may be disqualified.
**Input Format:** One line containing the two strings `s` and `t`, separated by a space.
**Constraints:**
- `1 <= |s|, |t| <= 2000`
- Strings have lowercase or uppercase letters only.
**Output Format:** One integer, the edit distance.
**Sample:** input `kitten sitting` → `3`
