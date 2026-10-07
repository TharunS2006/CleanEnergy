n = int(input())
a = list(map(int, input().split()))
total = 1
for i in range(1, n):
    total += a[i]
print(total)
