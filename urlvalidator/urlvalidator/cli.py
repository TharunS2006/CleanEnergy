"""Command-line interface:  python -m urlvalidator.cli <url> [<url> ...]   or   --trace, --info, --file urls.txt"""
import argparse, sys
from .validator import validate, machines


def main(argv=None):
    ap = argparse.ArgumentParser(prog="urlvalidator", description="Automata-based URL validator")
    ap.add_argument("urls", nargs="*", help="URLs to check")
    ap.add_argument("--file", help="text file with one URL per line")
    ap.add_argument("--trace", action="store_true", help="show the DFA state after every character")
    ap.add_argument("--info", action="store_true", help="show the size of the automata built from the URL grammar")
    a = ap.parse_args(argv)
    if a.info:
        nfa, dfa, mini = machines()
        print(f"NFA states: {nfa.size}\nDFA states (subset construction, with dead state): {dfa.size}\n"
              f"minimal DFA states: {mini.size}  (dead states: {len(mini.dead_states())})\nalphabet classes: {mini.n_classes}")
    urls = list(a.urls)
    if a.file:
        urls += [l.rstrip("\n") for l in open(a.file, encoding="utf-8") if l.strip()]
    bad = 0
    for u in urls:
        r = validate(u, trace=a.trace)
        print(f"{'VALID  ' if r.valid else 'INVALID'}  {u}")
        if r.valid:
            print("   " + ", ".join(f"{k}={v}" for k, v in r.parts.items() if v not in (None, "")))
        else:
            bad += 1
            print("   " + r.message)
            if r.expected: print("   expected one of: " + " ".join(r.expected))
        if a.trace:
            for i, ch, st, ph in r.trace: print(f"   {i:3d}  {ch!r:5}  state {st:<4} {ph}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
