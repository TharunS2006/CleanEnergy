t = int(input())
for _ in range(t):
    s = input().strip()
    st = []
    good = True
    for c in s:
        if c in "([{":
            st.append(c)
        else:
            if not st:
                good = False
                break
            top = st.pop()
            if (c == ')' and top != '(') or (c == ']' and top != '[') or (c == '}' and top != '{'):
                good = False
                break
    if st:
        good = False
    print("YES" if good else "NO")
