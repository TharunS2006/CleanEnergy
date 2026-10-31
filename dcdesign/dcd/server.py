"""Browser interface: python -m dcd.server [port]  ->  http://127.0.0.1:8000"""
import json, pathlib, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import designs, evaluate, security
from .model import Rule, HARDENING_ITEMS

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"
FIX = {"default-allow": "set the default action to deny and list only the flows that are needed", "any-any": "delete the rule and replace it by the specific flows of the design",
       "broad-rule": "replace the wildcard by the exact zones and port", "unauthorised-flow": "remove the rule or add it to the intended policy after a review",
       "unencrypted": "require TLS or IPsec on this flow", "shadowed-rule": "delete or reorder the rule", "missing-flow": "add the flow if the service needs it"}


def build(b):
    kind = b.get("kind", "resilient")
    base = designs.reference_design("resilient" if kind == "hardened" else kind, int(b.get("n_vms", 40)))
    if kind == "hardened":
        base, _ = designs.harden(designs.reference_design("basic", int(b.get("n_vms", 40))))
    if "rules" in b:
        base.rules = [Rule(r["src"], r["dst"], str(r["port"]), r["action"], bool(r.get("encrypted", True))) for r in b["rules"]]
        base.default_action = b.get("default_action", base.default_action)
    return base


def slim(r):
    r = dict(r)
    sec = dict(r["security"])
    sec["findings"] = [dict(f, fix=FIX.get(f["kind"], "")) for f in sec["findings"]]
    r["security"] = sec
    return r


def api_evaluate(b):
    d = build(b)
    r = slim(evaluate.evaluate(d, int(b.get("years", 1000))))
    r["rules"] = [vars(x) for x in d.rules]; r["default_action"] = d.default_action
    return r


def api_harden(b):
    d = build({"kind": b.get("kind", "basic"), "n_vms": b.get("n_vms", 40)})
    new, changes = designs.harden(d)
    years = int(b.get("years", 1000))
    return {"before": slim(evaluate.evaluate(d, years)), "after": slim(evaluate.evaluate(new, years)), "changes": changes,
            "still_to_do": security.hardening(new)["missing"]}


ROUTES = {"/api/evaluate": api_evaluate, "/api/harden": api_harden}


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
        except (ValueError, KeyError, TypeError, AssertionError) as e:
            self.send(400, json.dumps({"error": str(e)}), "application/json")

    def log_message(self, *a):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Data centre design evaluator on http://127.0.0.1:{port}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
