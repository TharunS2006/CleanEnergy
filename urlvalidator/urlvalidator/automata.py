"""Finite-automata toolkit, written from the textbook constructions and using only the standard library.

Pipeline:   regular expression --parse--> syntax tree --Thompson--> NFA --subset construction--> DFA --Moore--> minimal DFA

Characters are ASCII 0..127. Everything else (non-ASCII text) falls into one extra symbol class that no pattern accepts,
so such input always leads to the dead state. The alphabet is compressed: characters that no part of the pattern can
tell apart share one class, which keeps the transition tables small.
"""
from collections import deque

ASCII = 128                       # code points 0..127; class index of "everything else" is assigned later


# ----------------------------------------------------------------------------- regular-expression parser
class RegexError(ValueError):
    pass


class Parser:
    """alt := cat ('|' cat)* ;  cat := rep* ;  rep := atom ('*' | '+' | '?' | '{m}' | '{m,n}')* ;
       atom := '(' alt ')' | '[' set ']' | '\\' char | literal.   '.' is a literal dot, never a wildcard."""
    SPECIAL = set("|()[]*+?{}\\")

    def __init__(self, text):
        self.s, self.i = text, 0

    def parse(self):
        node = self.alt()
        if self.i != len(self.s):
            raise RegexError(f"unexpected {self.s[self.i]!r} at {self.i}")
        return node

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def alt(self):
        parts = [self.cat()]
        while self.peek() == "|":
            self.i += 1
            parts.append(self.cat())
        return parts[0] if len(parts) == 1 else ("alt", parts)

    def cat(self):
        parts = []
        while self.peek() not in (None, "|", ")"):
            parts.append(self.rep())
        if not parts:
            return ("eps",)
        return parts[0] if len(parts) == 1 else ("cat", parts)

    def rep(self):
        node = self.atom()
        while self.peek() in ("*", "+", "?", "{"):
            c = self.s[self.i]; self.i += 1
            if c == "*": node = ("star", node)
            elif c == "+": node = ("plus", node)
            elif c == "?": node = ("opt", node)
            else:
                j = self.s.index("}", self.i)
                spec = self.s[self.i:j]; self.i = j + 1
                lo, _, hi = spec.partition(",")
                lo = int(lo); hi = lo if "," not in spec else (int(hi) if hi else None)
                node = ("rep", node, lo, hi)
        return node

    def atom(self):
        c = self.peek()
        if c is None:
            raise RegexError("pattern ended early")
        self.i += 1
        if c == "(":
            node = self.alt()
            if self.peek() != ")":
                raise RegexError("missing )")
            self.i += 1
            return node
        if c == "[":
            return ("set", self.charset())
        if c == "\\":
            e = self.s[self.i]; self.i += 1
            return ("set", frozenset([ord(e)]))
        if c in self.SPECIAL:
            raise RegexError(f"unexpected {c!r} at {self.i - 1}")
        return ("set", frozenset([ord(c)]))

    def charset(self):
        chars = set()
        while self.peek() != "]":
            if self.peek() is None:
                raise RegexError("missing ]")
            a = self.class_char()
            if self.peek() == "-" and self.s[self.i + 1:self.i + 2] not in ("]", ""):
                self.i += 1
                b = self.class_char()
                chars.update(range(a, b + 1))
            else:
                chars.add(a)
        self.i += 1
        return frozenset(chars)

    def class_char(self):
        c = self.s[self.i]; self.i += 1
        if c == "\\":
            c = self.s[self.i]; self.i += 1
        return ord(c)


# ----------------------------------------------------------------------------- Thompson construction
class NFA:
    def __init__(self):
        self.eps = []            # eps[s]  = list of states
        self.moves = []          # moves[s] = list of (frozenset of code points, target)
        self.start = self.accept = None

    def new(self):
        self.eps.append([]); self.moves.append([])
        return len(self.eps) - 1

    @property
    def size(self):
        return len(self.eps)


def thompson(tree):
    nfa = NFA()

    def build(node):
        kind = node[0]
        s, t = nfa.new(), nfa.new()
        if kind == "eps":
            nfa.eps[s].append(t)
        elif kind == "set":
            nfa.moves[s].append((node[1], t))
        elif kind == "cat":
            cur = s
            for part in node[1]:
                a, b = build(part)
                nfa.eps[cur].append(a); cur = b
            nfa.eps[cur].append(t)
        elif kind == "alt":
            for part in node[1]:
                a, b = build(part)
                nfa.eps[s].append(a); nfa.eps[b].append(t)
        elif kind == "star":
            a, b = build(node[1])
            nfa.eps[s] += [a, t]; nfa.eps[b] += [a, t]
        elif kind == "plus":
            a, b = build(node[1])
            nfa.eps[s].append(a); nfa.eps[b] += [a, t]
        elif kind == "opt":
            a, b = build(node[1])
            nfa.eps[s] += [a, t]; nfa.eps[b].append(t)
        elif kind == "rep":                      # expand x{m,n} into copies, as the textbook does
            _, sub, lo, hi = node
            cur = s
            for _ in range(lo):
                a, b = build(sub); nfa.eps[cur].append(a); cur = b
            if hi is None:
                a, b = build(("star", sub)); nfa.eps[cur].append(a); cur = b
            else:
                for _ in range(hi - lo):
                    a, b = build(sub)
                    nfa.eps[cur] += [a, t]; cur = b
            nfa.eps[cur].append(t)
        return s, t

    nfa.start, nfa.accept = build(tree)
    return nfa


# ----------------------------------------------------------------------------- DFA
class DFA:
    def __init__(self, delta, start, accepting, char_class, n_classes):
        self.delta = delta                    # delta[state][class] -> state   (total function, a dead state exists)
        self.start = start
        self.accepting = frozenset(accepting)
        self.char_class = char_class          # list of length 128: code point -> class
        self.other = n_classes - 1            # class of every non-ASCII character
        self.n_classes = n_classes
        self._live = None

    @property
    def size(self):
        return len(self.delta)

    def klass(self, ch):
        o = ord(ch)
        return self.char_class[o] if o < ASCII else self.other

    def step(self, state, ch):
        return self.delta[state][self.klass(ch)]

    def accepts(self, text):
        d, q, cc, other = self.delta, self.start, self.char_class, self.other
        for ch in text:
            o = ord(ch)
            q = d[q][cc[o] if o < ASCII else other]
        return q in self.accepting

    @property
    def live(self):
        """States from which some accepting state is still reachable. The rest are dead (the sink)."""
        if self._live is None:
            rev = [[] for _ in self.delta]
            for s, row in enumerate(self.delta):
                for t in set(row): rev[t].append(s)
            live, queue = set(self.accepting), deque(self.accepting)
            while queue:
                for p in rev[queue.popleft()]:
                    if p not in live: live.add(p); queue.append(p)
            self._live = live
        return self._live

    def dead_states(self):
        return [s for s in range(self.size) if s not in self.live]

    def expected(self, state, limit=14):
        """Printable characters that keep the input alive from this state, as a short readable list."""
        chars = [chr(c) for c in range(33, 127) if self.delta[state][self.char_class[c]] in self.live]
        return chars if len(chars) <= limit else chars[:limit] + ["..."]

    def transition_count(self):
        return sum(1 for s in range(self.size) for k in range(self.n_classes) if self.delta[s][k] in self.live and s in self.live)


def alphabet_classes(nfa):
    """Split 0..127 into classes of characters that every set in the pattern treats alike."""
    sets = {cs for st in nfa.moves for cs, _ in st}
    sets = sorted(sets, key=lambda z: sorted(z))
    sig_to_class, char_class = {}, []
    for c in range(ASCII):
        sig = tuple(c in cs for cs in sets)
        char_class.append(sig_to_class.setdefault(sig, len(sig_to_class)))
    return char_class, len(sig_to_class) + 1                  # +1: the "non-ASCII" class


def subset_construction(nfa):
    char_class, n_classes = alphabet_classes(nfa)
    members = [[] for _ in range(n_classes)]
    for c, k in enumerate(char_class): members[k].append(c)
    rep = [m[0] for m in members[:-1]]                         # one representative per ASCII class

    def closure(states):
        seen, stack = set(states), list(states)
        while stack:
            for t in nfa.eps[stack.pop()]:
                if t not in seen: seen.add(t); stack.append(t)
        return frozenset(seen)

    start, empty = closure([nfa.start]), frozenset()
    ids, order, delta = {start: 0}, [start], []
    i = 0
    while i < len(order):
        cur = order[i]; i += 1
        row = []
        for k in range(n_classes):
            if k == n_classes - 1:                             # non-ASCII text is never part of a URL
                tgt = empty
            else:
                c = rep[k]
                nxt = {t for s in cur for cs, t in nfa.moves[s] if c in cs}
                tgt = closure(nxt) if nxt else empty
            if tgt not in ids: ids[tgt] = len(order); order.append(tgt)
            row.append(ids[tgt])
        delta.append(row)
    accepting = [ids[s] for s in order if nfa.accept in s]
    return DFA(delta, 0, accepting, char_class, n_classes)


def minimise(dfa):
    """Moore's partition refinement: start from {accepting, rejecting} and split blocks until no state in a block
    behaves differently on any symbol class. The result has the fewest states of any DFA for the same language."""
    n, k = dfa.size, dfa.n_classes
    block = [1 if s in dfa.accepting else 0 for s in range(n)]
    count = len(set(block))
    while True:
        sig, new, nb = {}, [], 0
        for s in range(n):
            key = (block[s], tuple(block[t] for t in dfa.delta[s]))
            if key not in sig: sig[key] = nb; nb += 1
            new.append(sig[key])
        block = new
        if nb == count: break
        count = nb
    order = {}
    for s in range(n):                                        # number blocks in order of first appearance, start = 0
        order.setdefault(block[dfa.start] if s == 0 else block[s], len(order))
    first = {}
    for s in range(n): first.setdefault(block[s], s)
    delta = [[order[block[t]] for t in dfa.delta[first[b]]] for b in sorted(order, key=order.get)]
    accepting = {order[block[s]] for s in dfa.accepting}
    return DFA(delta, order[block[dfa.start]], accepting, dfa.char_class, dfa.n_classes)


def compile_regex(pattern):
    """pattern -> (nfa, dfa, minimal dfa)"""
    nfa = thompson(Parser(pattern).parse())
    dfa = subset_construction(nfa)
    return nfa, dfa, minimise(dfa)


def equivalent(a, b):
    """Product construction: the two DFAs accept the same language iff no reachable pair (p, q) has exactly one accepting."""
    syms = [chr(c) for c in range(ASCII)] + ["é"]
    seen, queue = {(a.start, b.start)}, deque([(a.start, b.start)])
    while queue:
        p, q = queue.popleft()
        if (p in a.accepting) != (q in b.accepting):
            return False
        for ch in syms:
            nxt = (a.step(p, ch), b.step(q, ch))
            if nxt not in seen: seen.add(nxt); queue.append(nxt)
    return True
