n = int(input())
a = list(map(int, input().split()))
mx = 0
for x in a:
    if x < mx:
        mx = x
print(mx)
