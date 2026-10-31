"""Browser interface: python -m urlvalidator.server [port]   ->  http://127.0.0.1:8000"""
import json, pathlib, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from .validator import validate, machines

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"


def result_json(r):
    return {"url": r.url, "valid": r.valid, "status": r.status, "position": r.position, "char": r.char, "message": r.message,
            "expected": r.expected, "parts": r.parts,
            "trace": [{"i": i, "char": c, "state": s, "phase": p} for i, c, s, p in r.trace]}


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/validate":
            q = parse_qs(u.query).get("url", [""])[0]
            return self.send(200, json.dumps(result_json(validate(q, trace=True))), "application/json")
        if u.path == "/api/info":
            n, d, m = machines()
            return self.send(200, json.dumps({"nfa": n.size, "dfa": d.size, "minimal": m.size, "classes": m.n_classes}), "application/json")
        if u.path in ("/", "/index.html"):
            return self.send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
        self.send(404, "Not found", "text/plain")

    def do_POST(self):                      # batch: body is JSON {"urls": [...]}
        if self.path != "/api/batch":
            return self.send(404, "Not found", "text/plain")
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        out = [result_json(validate(u)) for u in body.get("urls", [])[:500]]
        self.send(200, json.dumps(out), "application/json")

    def log_message(self, *a):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"URL validator on http://127.0.0.1:{port}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
