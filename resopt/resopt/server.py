"""Browser interface: python -m resopt.server [port]  ->  http://127.0.0.1:8000"""
import json, pathlib, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import cpu, memory, disk, optimizer
from .cpu import Proc

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"


def api_cpu(body):
    procs = [Proc(str(p["pid"]), int(p["arrival"]), int(p["burst"]), int(p.get("priority", 0))) for p in body["procs"]]
    rec = optimizer.recommend_cpu(procs, int(body.get("quantum", 4)))
    return {"recommended": rec["recommended"], "why": rec["why"], "improvement": rec["improvement"], "best": rec["best"],
            "runs": {a: {"metrics": r["metrics"], "gantt": r["gantt"], "rows": r["rows"]} for a, r in rec["runs"].items()}}


def api_memory(body):
    refs = [int(x) for x in body["refs"]]; frames = int(body["frames"])
    rec = optimizer.recommend_memory(refs, frames)
    return {"recommended": rec["recommended"], "optimal": rec["optimal_faults"], "gap": rec["gap_to_optimal"], "improvement": rec["improvement"],
            "runs": {a: {"faults": r["faults"], "hits": r["hits"], "fault_rate": r["fault_rate"], "steps": r["steps"]} for a, r in rec["runs"].items()}}


def api_disk(body):
    reqs = [int(x) for x in body["requests"]]
    rec = optimizer.recommend_disk(reqs, int(body["head"]), int(body.get("cylinders", 200)), int(body.get("direction", 1)))
    return {"recommended": rec["recommended"], "improvement": rec["improvement"],
            "runs": {a: {"total": r["total"], "average": r["average"], "path": r["path"]} for a, r in rec["runs"].items()}}


ROUTES = {"/api/cpu": api_cpu, "/api/memory": api_memory, "/api/disk": api_disk}


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
    print(f"Resource optimizer on http://127.0.0.1:{port}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
