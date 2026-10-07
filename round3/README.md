# IEEE Bug Quest – Round 3 Final (top 3, 60 min, 400 pts)

| ID | Name | Pts | Bugs fixed by students |
|----|------|-----|------------------------|
| Q1 | LRU Cache | 100 | GET/PUT do not refresh recency, evicts one too early, missing key not -1 |
| Q2 | Resource Allocation (0/1 Knapsack) | 150 | table size W instead of W+1, weight/value read swapped, forward (unbounded) loop, int overflow |
| Q3 | Counting Chip Islands (BFS on a grid) | 150 | wrong direction array, row bound `<=`, column loop uses rows |

Every question has `buggy.*` / `fixed.*` in C++, Java and Python and hidden tests in `Qn/tests/`.
`python3 build_tests.py` regenerates tests; `python3 validate.py` checks all 18 programs
(each fixed passes every test, each buggy fails at least one). `zips/` has HackerRank upload zips.
Keep `fixed.*` private. See FORM_FIELDS.md for the Create Challenge form values.
