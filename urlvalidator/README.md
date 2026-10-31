# Automata-Based URL Validator

Validates URLs with a minimal DFA built from the URL grammar. The regular expression is parsed, turned into an NFA (Thompson), a DFA (subset construction) and a minimal DFA (Moore) by `urlvalidator/automata.py`; nothing outside the Python standard library is used.

```
python -m unittest discover -s tests          # 21 tests
python -m urlvalidator.cli https://example.com/a?b=1 --trace
python -m urlvalidator.cli --info             # automaton sizes
python -m urlvalidator.server 8000            # http://127.0.0.1:8000
python bench.py                               # writes bench_results.json
cd report && python charts.py && python build.py   # rebuilds the report (needs matplotlib, LibreOffice)
```

Folders: `urlvalidator/` code, `web/` browser page, `tests/`, `report/` the project report (DOCX and PDF in `report/output/`).
