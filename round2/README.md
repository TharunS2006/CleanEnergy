# IEEE Bug Quest – Round 2 (top 10, 60 min, 400 pts)

| ID | Name | Level | Pts | Bugs fixed by students |
|----|------|-------|-----|------------------------|
| Q1 | Balanced Brackets | Moderate | 50 | pop on empty stack, `]` matched with `(`, leftover openers ignored |
| Q2 | Shortest Network Latency (Dijkstra) | Hard | 100 | directed-only edges, max-heap, no stale-entry skip, int overflow |
| Q3 | Course Scheduler (Topological Sort) | Hard | 100 | stack instead of min-heap, no CYCLE detection |
| Q4 | Edit Distance | Very Hard | 150 | dp size, missing base cases, off-by-one indexing, reversed cost, missing insert |

Every question has `buggy.*` / `fixed.*` in C++, Java and Python and hidden tests in `Qn/tests/`.
`python3 build_tests.py` regenerates tests; `python3 validate.py` checks all 24 programs
(each fixed passes every test, each buggy fails at least one). `zips/` has HackerRank upload zips.
Keep `fixed.*` private. See FORM_FIELDS.md for the Create Challenge form values.
