"""Browser interface: python -m vmdr.server [port]  ->  http://127.0.0.1:8000"""
import json, pathlib, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import avail, sim, dr, backup

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"


def _params(b):
    p = sim.Params()
    for k in ("host_mtbf", "host_mttr", "zone_mtbf", "zone_mttr", "region_mtbf", "region_mttr", "restart_minutes", "failover_minutes", "detect_minutes"):
        if k in b: setattr(p, k, float(b[k]))
    return p


def api_avail(b):
    a = avail.availability(float(b["mtbf"]), float(b["mttr"]))
    rows = [{"copies": n, "availability": avail.parallel(*[a] * n)} for n in (1, 2, 3)]
    for r in rows: r["downtime_min_per_year"] = avail.downtime_minutes_per_year(r["availability"]); r["nines"] = avail.nines(r["availability"])
    return {"availability": a, "nines": avail.nines(a), "downtime_min_per_year": avail.downtime_minutes_per_year(a), "copies": rows,
            "sla": [{"target": t, **avail.sla_downtime(t)} for t in avail.SLA_TABLE]}


def api_compare(b):
    years = max(100, min(int(b.get("years", 2000)), 20000))
    tier = dr.TIERS[b.get("tier", "warm-standby")]
    res = sim.compare(_params(b), years, int(b.get("seed", 1)), tier)
    ev = dr.dr_events(_params(b), tier, years)
    return {"years": years, "tier": tier.name, "results": res, "dr": ev}


def api_plan(b):
    r = dr.plan(float(b["target"]), b.get("rto"), b.get("rpo"), _params(b), 4000)
    return {"rows": r["rows"], "recommended": r["recommended"]}


def api_backup(b):
    i, p = float(b["interval"]), float(b.get("success", 1.0))
    return {"mean": backup.mean_data_age_minutes(i, p), "p99": backup.percentile_data_age_minutes(i, p),
            "restore": backup.restore_minutes(float(b.get("size_gb", 500)), float(b.get("throughput", 100)))}


ROUTES = {"/api/avail": api_avail, "/api/compare": api_compare, "/api/plan": api_plan, "/api/backup": api_backup}


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self.send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
        self.send(404, "Not found", "text/plain")

    def do_POST(self):
        fn = ROUTES.get(self.path)
        if fn is None:
            return self.send(404, "Not found", "text/plain")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            self.send(200, json.dumps(fn(body)), "application/json")
        except (ValueError, KeyError, TypeError) as e:
            self.send(400, json.dumps({"error": str(e)}), "application/json")

    def log_message(self, *a):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"VM availability and DR planner on http://127.0.0.1:{port}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
