# VM Availability and Disaster Recovery

Availability mathematics, a Monte Carlo failure simulator for six VM designs, four disaster-recovery tiers, a backup calculator and a planner that recommends the cheapest design meeting an availability target and RTO/RPO limits. Python standard library only.

```
python -m unittest discover -s tests          # 39 tests (a few seconds)
python -m vmdr.cli demo
python -m vmdr.cli plan --target 0.9999 --rto 60 --rpo 15
python -m vmdr.server 8000                    # http://127.0.0.1:8000
python bench.py                               # experiments, writes bench_results.json
cd report && python charts.py && python build.py   # rebuild the report (needs matplotlib, LibreOffice)
```
The failure rates, repair times, DR-tier parameters and costs are model assumptions (see report, Tables 5.2 and 5.3), not provider measurements.
