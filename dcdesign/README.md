# Secure and Resilient Virtualized Data Centre Design

Evaluates a virtualized data-centre design for capacity (placement, N+1), security (first-match firewall rules, routes from the internet, hardening checklist) and resilience (every single and double component failure, simulated availability), and applies the technical fixes automatically. Python standard library only.

```
python -m unittest discover -s tests          # 34 tests
python -m dcd.cli compare                     # basic, segmented, resilient
python -m dcd.cli harden basic                # automatic remediation, before and after
python -m dcd.server 8000                     # http://127.0.0.1:8000
python bench.py                               # experiments, writes bench_results.json
cd report && python charts.py && python build.py   # rebuild the report (needs matplotlib, LibreOffice)
```
Failure rates, scoring weights and the intended firewall policy are model assumptions (see report, Chapter 5), not measurements of a real site.
