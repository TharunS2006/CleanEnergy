"""The URL language, written as one regular expression built from named pieces.

It is a practical subset of RFC 3986 (scheme://host[:port][/path][?query][#fragment]) with the host rules of RFC 1035 / 1123.
The pattern uses only features that are also valid in Python's `re`, so the same string can be handed to `re.fullmatch`
as an independent check of the automaton.
"""

def ci(word):                                   # case-insensitive literal: http -> [hH][tT][tT][pP]
    return "".join(f"[{c.lower()}{c.upper()}]" for c in word)

SCHEME = f"({ci('http')}{ci('s')}?|{ci('ftp')}{ci('s')}?)"
OCTET = "(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])"
IPV4 = f"{OCTET}\\.{OCTET}\\.{OCTET}\\.{OCTET}"
LABEL = "[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?"          # 1..63 letters, digits or hyphens; no hyphen at either end
TLD = "[A-Za-z]{2,63}"
DOMAIN = f"({LABEL}\\.)+{TLD}"
HOST = f"({ci('localhost')}|{IPV4}|{DOMAIN})"
PORT_NUMBER = "(6553[0-5]|655[0-2][0-9]|65[0-4][0-9][0-9]|6[0-4][0-9][0-9][0-9]|[1-5][0-9][0-9][0-9][0-9]|[1-9][0-9]{0,3})"
PORT = f"(:{PORT_NUMBER})?"
PCHAR = "([A-Za-z0-9\\-._~!$&'()*+,;=:@]|%[0-9A-Fa-f][0-9A-Fa-f])"
PATH = f"(/{PCHAR}*)*"
QUERY = f"(\\?({PCHAR}|[/?])*)?"
FRAGMENT = f"(#({PCHAR}|[/?])*)?"

URL = f"{SCHEME}://{HOST}{PORT}{PATH}{QUERY}{FRAGMENT}"

# the named pieces, used by the report and the size measurements
PARTS = {"scheme": SCHEME, "ipv4": IPV4, "label": LABEL, "domain": DOMAIN, "host": HOST, "port": PORT,
         "path": PATH, "query": QUERY, "fragment": FRAGMENT, "full URL": URL}
