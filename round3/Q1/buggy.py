from collections import OrderedDict
import sys
c, q = map(int, sys.stdin.readline().split())
cache = OrderedDict()
out = []
for _ in range(q):
    parts = sys.stdin.readline().split()
    if parts[0] == "GET":
        k = int(parts[1])
        out.append(str(cache.get(k, 0)))
    else:
        k, v = int(parts[1]), int(parts[2])
        cache[k] = v
        if len(cache) >= c:
            cache.popitem(last=False)
print("\n".join(out))
