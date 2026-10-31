"""URL validator driven by the minimal DFA for the URL language."""
from dataclasses import dataclass, field
from functools import lru_cache

from .automata import compile_regex
from .grammar import URL


@lru_cache(maxsize=1)
def machines():
    """(nfa, dfa, minimal dfa) for the full URL pattern; built once, takes a few milliseconds."""
    return compile_regex(URL)


@dataclass
class Result:
    url: str
    valid: bool
    status: str                       # "valid", "invalid" or "incomplete"
    position: int = -1                # index of the first character that cannot belong to any URL
    char: str = ""
    message: str = ""
    expected: list = field(default_factory=list)
    parts: dict = field(default_factory=dict)
    trace: list = field(default_factory=list)     # one (index, char, state, phase) per character


def phase_of(prefix):
    """Which part of the URL the characters read so far belong to. A plain scan is enough once the delimiters are known."""
    if "://" not in prefix:
        return "scheme"
    rest = prefix.split("://", 1)[1]
    if "#" in rest:                       # the latest part that has started wins: fragment, then query, then path
        return "fragment"
    if "?" in rest:
        return "query"
    if "/" in rest:
        return "path"
    return "port" if ":" in rest else "host"


HINTS = {
    "scheme": "the scheme must be http, https, ftp or ftps, followed by ://",
    "host": "a host is a name such as example.com, localhost, or an IPv4 address with every part from 0 to 255; "
            "labels use letters, digits and inner hyphens, at most 63 characters each",
    "port": "a port is a number from 1 to 65535",
    "path": "a path may contain letters, digits, - . _ ~ ! $ & ' ( ) * + , ; = : @ and %XX escapes; spaces are not allowed",
    "query": "a query may contain the same characters as a path, plus / and ?",
    "fragment": "a fragment may contain the same characters as a query",
}


def split_parts(url):
    """Components of an already accepted URL. The delimiters / ? # cannot occur inside the earlier parts, so cutting at the
    first one of each is exact."""
    scheme, rest = url.split("://", 1)
    fragment = query = None
    if "#" in rest: rest, fragment = rest.split("#", 1)
    if "?" in rest: rest, query = rest.split("?", 1)
    path = ""
    if "/" in rest: i = rest.index("/"); rest, path = rest[:i], rest[i:]
    host, port = rest, None
    if ":" in rest: host, port = rest.rsplit(":", 1)
    parts = {"scheme": scheme.lower(), "host": host, "port": port, "path": path or "/", "query": query, "fragment": fragment}
    parts["host_type"] = "localhost" if host.lower() == "localhost" else ("ipv4" if host.replace(".", "").isdigit() else "domain")
    return parts


def ip_quad_problem(url):
    """For hosts written as four dotted numbers: (index, text) of the first part above 255, or None. Used only to give a
    better message; the accept / reject decision itself is always made by the automaton."""
    if "://" not in url:
        return None
    start = url.index("://") + 3
    end = min([i for i in (url.find(c, start) for c in "/?#:") if i >= 0] or [len(url)])
    host = url[start:end]
    bits = host.split(".")
    if len(bits) == 4 and all(b.isdigit() for b in bits):
        at = start
        for b in bits:
            if int(b) > 255:
                return at, b
            at += len(b) + 1
    return None


def validate(url, trace=False):
    nfa, dfa, mini = machines()
    state, trail = mini.start, []
    for i, ch in enumerate(url):
        nxt = mini.step(state, ch)
        if trace:
            trail.append((i, ch, nxt, phase_of(url[:i + 1])))
        if nxt not in mini.live:
            quad = ip_quad_problem(url)
            if quad:                                 # a dotted number with a part above 255: say so instead of blaming '/'
                return Result(url, False, "invalid", quad[0], url[quad[0]], f"{quad[1]!r} is not a valid IPv4 part: every part must be "
                              "from 0 to 255.", [], {}, trail)
            phase = phase_of(url[:i + 1]) if url else "scheme"
            if i > 0 and phase_of(url[:i]) != phase and phase in ("path", "query", "fragment"):
                phase = phase_of(url[:i])
            return Result(url, False, "invalid", i, ch, f"Unexpected {ch!r} at position {i}: {HINTS[phase]}.",
                          mini.expected(state), {}, trail)
        state = nxt
    if state in mini.accepting:
        return Result(url, True, "valid", message="Valid URL.", parts=split_parts(url), trace=trail)
    phase = phase_of(url)
    quad = ip_quad_problem(url)
    if quad:                                         # looks like an IPv4 address but a part is out of range
        pos, text = quad
        return Result(url, False, "invalid", pos, url[pos], f"{text!r} is not a valid IPv4 part: every part must be from 0 to 255.",
                      [], {}, trail)
    return Result(url, False, "incomplete", len(url), "", f"The URL ends too early: {HINTS[phase]}.", mini.expected(state), {}, trail)
