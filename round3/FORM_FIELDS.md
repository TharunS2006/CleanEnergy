# HackerRank "Create Challenge" values – Round 3 final (Details page)

Create these in a NEW private contest for the top 3. Languages: C++, Java 8+, Python 3. Paste each language's buggy.* as its stub (Languages tab).
Tags for all: debugging, round3

---
## Q1 (Score 100)
**Challenge Name:** R3-Q1 - LRU Cache
**Description:** Fix the buggy LRU cache simulation.
**Problem Statement:**
Simulate an LRU (least recently used) cache with capacity `c`. `GET k` prints the value for key `k`, or `-1` if it is not in the cache, and counts as a use of `k`. `PUT k v` inserts or updates key `k` and also counts as a use. When the cache would exceed its capacity, the least recently used key is removed. The given program contains bugs. Fix them so it gives the correct output for all test cases. Keep the original structure of the code; fully rewritten solutions may be disqualified.
**Input Format:**
The first line contains `c` and `q`.

Each of the next `q` lines is `GET k` or `PUT k v`.
**Constraints:**
- `1 <= c <= 10^5`
- `1 <= q <= 10^5`
- `1 <= k <= 10^9`, `1 <= v <= 10^9`
**Output Format:** For every `GET`, print one line: the value or `-1`.
**Sample:** input `2 6` / `PUT 1 1` / `PUT 2 2` / `GET 1` / `PUT 3 3` / `GET 2` / `GET 1` → `1` / `-1` / `1`

---
## Q2 (Score 150)
**Challenge Name:** R3-Q2 - Resource Allocation
**Description:** Fix the buggy 0/1 knapsack dynamic programming program.
**Problem Statement:**
Choose items, each at most once, so that the total weight is at most `W` and the total value is as large as possible. Print the maximum total value. The given program contains bugs. Fix them so it gives the correct output for all test cases. Keep the original structure of the code; fully rewritten solutions may be disqualified.
**Input Format:**
The first line contains `n` and `W`.

Each of the next `n` lines contains `weight value`.
**Constraints:**
- `1 <= n <= 500`
- `1 <= W <= 10^4`
- `1 <= weight <= 10^4`, `1 <= value <= 10^9`
**Output Format:** One integer, the maximum total value.
**Sample:** input `3 50` / `10 60` / `20 100` / `30 120` → `220`

---
## Q3 (Score 150)
**Challenge Name:** R3-Q3 - Counting Chip Islands
**Description:** Fix the buggy BFS that counts connected groups of 1s in a grid.
**Problem Statement:**
In a grid of `0`s and `1`s, count the groups of `1`s that are connected up, down, left or right. The given program contains bugs. Fix them so it gives the correct output for all test cases. Keep the original structure of the code; fully rewritten solutions may be disqualified.
**Input Format:**
The first line contains `r` and `c`.

Each of the next `r` lines is a string of `c` characters, `0` or `1`.
**Constraints:**
- `1 <= r, c <= 1000`
**Output Format:** One integer, the number of groups.
**Sample:** input `4 5` / `11000` / `11000` / `00100` / `00011` → `3`
