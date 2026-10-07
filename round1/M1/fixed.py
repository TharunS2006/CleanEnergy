k = int(input())
s = input()
k = k % 26
res = []
for c in s:
    if c.islower():
        res.append(chr(ord('a') + (ord(c) - ord('a') + k) % 26))
    elif c.isupper():
        res.append(chr(ord('A') + (ord(c) - ord('A') + k) % 26))
    else:
        res.append(c)
print("".join(res))
