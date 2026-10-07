from collections import OrderedDict
import sys
c, q = map(int, sys.stdin.readline().split())
cache = OrderedDict()
out = []
for _ in range(q):
    parts = sys.stdin.readline().split()
    if parts[0] == "GET":
        k = int(parts[1])
        if k in cache:
            cache.move_to_end(k)
            out.append(str(cache[k]))
        else:
            out.append("-1")
    else:
        k, v = int(parts[1]), int(parts[2])
        cache[k] = v
        cache.move_to_end(k)
        if len(cache) > c:
            cache.popitem(last=False)
print("\n".join(out))
