"""A small Azure Resource Manager REST client.

Why not the SDKs: Cost Management, Resource Graph, Monitor metrics, Advisor
and the Activity Log are all simple JSON endpoints, and one client with
proper retry and paging is easier to reason about (and test) than five SDKs.

Handles:
  - bearer tokens from any azure-identity credential, refreshed before expiry
  - HTTP 429 and 5xx: waits for Retry-After (or Cost Management's own
    x-ms-ratelimit-*-retry-after headers), up to 4 retries, max 60 s each
  - paging through `nextLink` (GET or POST) and Resource Graph `$skipToken`
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

ARM = "https://management.azure.com"
SCOPE = "https://management.azure.com/.default"
MAX_RETRIES = 4


class ArmError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message


def _default_opener(method, url, headers, data, timeout):
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def _retry_after(headers: dict) -> float:
    lower = {k.lower(): v for k, v in headers.items()}
    candidates = [v for k, v in lower.items() if k == "retry-after" or (k.startswith("x-ms-ratelimit") and k.endswith("retry-after"))]
    waits = []
    for v in candidates:
        try:
            waits.append(float(v))
        except (TypeError, ValueError):
            pass
    return min(60.0, max(waits)) if waits else 0.0


class ArmClient:
    def __init__(self, credential, timeout: float = 45, opener=None, sleep=time.sleep):
        self.credential = credential
        self.timeout = timeout
        self.opener = opener or _default_opener
        self.sleep = sleep
        self._token = None
        self._expires = 0.0

    def _bearer(self) -> str:
        if not self._token or time.time() > self._expires - 300:
            tok = self.credential.get_token(SCOPE)
            self._token, self._expires = tok.token, float(tok.expires_on)
        return self._token

    def request(self, method: str, url: str, body: dict | None = None, params: dict | None = None) -> dict:
        if not url.startswith("http"):
            url = ARM + url
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(MAX_RETRIES + 1):
            headers = {"Authorization": f"Bearer {self._bearer()}", "Accept": "application/json"}
            if data is not None:
                headers["Content-Type"] = "application/json"
            status, resp_headers, raw = self.opener(method, url, headers, data, self.timeout)
            if status in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                self.sleep(_retry_after(resp_headers) or min(30.0, 2.0 * 2 ** attempt))
                continue
            try:
                payload = json.loads(raw.decode() or "{}") if raw else {}
            except ValueError:
                payload = {}
            if status >= 400:
                err = payload.get("error", {}) if isinstance(payload, dict) else {}
                raise ArmError(status, err.get("code", "Error"), err.get("message", raw[:200].decode(errors="ignore")))
            return payload
        raise ArmError(429, "TooManyRequests", "Azure kept asking CloudPulse to slow down.")

    def get(self, url, params=None):
        return self.request("GET", url, params=params)

    def get_all(self, url, params=None, limit_pages: int = 50) -> list:
        items, page = [], self.get(url, params)
        for _ in range(limit_pages):
            items.extend(page.get("value", []))
            nxt = page.get("nextLink")
            if not nxt:
                break
            page = self.get(nxt)
        return items

    def post_all_rows(self, url, body, params=None, limit_pages: int = 50) -> tuple[list[str], list[list]]:
        """Cost Management query: returns (column names, all rows)."""
        page = self.request("POST", url, body=body, params=params)
        props = page.get("properties", {})
        columns = [c.get("name") for c in props.get("columns", [])]
        rows = list(props.get("rows", []))
        for _ in range(limit_pages):
            nxt = props.get("nextLink")
            if not nxt:
                break
            page = self.request("POST", nxt, body=body)
            props = page.get("properties", {})
            rows.extend(props.get("rows", []))
        return columns, rows

    def resource_graph(self, subscription_id: str, query: str, limit_pages: int = 50) -> list[dict]:
        url = "/providers/Microsoft.ResourceGraph/resources"
        params = {"api-version": "2022-10-01"}
        options = {"$top": 1000, "resultFormat": "objectArray"}
        out = []
        for _ in range(limit_pages):
            page = self.request("POST", url, body={"subscriptions": [subscription_id], "query": query,
                                                   "options": options}, params=params)
            out.extend(page.get("data", []))
            token = page.get("$skipToken")
            if not token:
                break
            options = {**options, "$skipToken": token}
        return out
