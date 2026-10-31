# CPU, Memory and I/O Resource Optimization

Simulators for CPU scheduling (FCFS, SJF, SRTF, PRIORITY, PRIORITY-P, RR), page replacement (FIFO, LRU, OPT, CLOCK) and disk scheduling (FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK), plus an optimizer that compares them on one workload and recommends the best. Python standard library only.

```
python -m unittest discover -s tests          # 29 tests
python -m resopt.cli demo                     # textbook examples
python -m resopt.server 8000                  # http://127.0.0.1:8000
python bench.py                               # experiments, writes bench_results.json
cd report && python charts.py && python build.py   # rebuild the report (needs matplotlib, LibreOffice)
```
