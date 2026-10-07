#!/usr/bin/env python3
"""Checks every buggy.*/fixed.* in each question folder against tests/: fixed must pass all, buggy must fail >=1."""
import glob, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); tmp = tempfile.mkdtemp(); ok = True
env = dict(os.environ); env.pop("JAVA_TOOL_OPTIONS", None)
def cmd(path, tag):
    ext = path.rsplit(".", 1)[1]
    if ext == "py": return ["python3", path]
    if ext == "cpp":
        exe = os.path.join(tmp, tag); subprocess.run(["g++", "-O2", "-o", exe, path], check=True); return [exe]
    jd = os.path.join(tmp, tag); os.makedirs(jd); shutil.copy(path, os.path.join(jd, "Main.java"))
    subprocess.run(["javac", "-d", jd, os.path.join(jd, "Main.java")], check=True, env=env, capture_output=True)
    return ["java", "-cp", jd, "Main"]
for q in sorted(d for d in os.listdir(HERE) if os.path.isdir(os.path.join(HERE, d))):
    qd = os.path.join(HERE, q); tests = sorted(glob.glob(os.path.join(qd, "tests", "*.in")))
    for kind in ("buggy", "fixed"):
        for f in sorted(glob.glob(os.path.join(qd, kind + ".*"))):
            c = cmd(f, f"{q}_{kind}_{f.rsplit('.',1)[1]}"); res = []
            for t in tests:
                exp = open(t[:-3] + ".out").read().strip()
                try:
                    p = subprocess.run(c, input=open(t).read(), capture_output=True, text=True, errors="replace", timeout=10, env=env)
                    res.append(p.returncode == 0 and p.stdout.strip() == exp)
                except subprocess.TimeoutExpired: res.append(False)
            good = all(res) if kind == "fixed" else not all(res)
            ok &= good
            print(f"{q} {os.path.basename(f):12s} pass {sum(res):2d}/{len(res):2d}  {'OK' if good else 'PROBLEM'}")
shutil.rmtree(tmp); sys.exit(0 if ok else 1)
