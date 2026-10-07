n, t = map(int, input().split())
a = list(map(int, input().split()))
lo, hi, ans = 0, n, -1
while lo < hi:
    mid = lo + (hi - lo) // 2
    if a[mid] == t:
        ans = mid
        lo = mid + 1
    elif a[mid] < t:
        lo = mid + 1
    else:
        hi = mid - 1
print(ans)
