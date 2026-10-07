s = input().strip()
last = {}
left = best = 0
for i, c in enumerate(s):
    if c in last:
        left = last[c] + 1
    last[c] = i
    best = max(best, i - left)
print(best)
