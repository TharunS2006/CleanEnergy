t = int(input())
for _ in range(t):
    s = input().strip()
    st = []
    good = True
    for c in s:
        if c in "([{":
            st.append(c)
        else:
            top = st.pop()
            if (c == ')' and top != '(') or (c == ']' and top != '(') or (c == '}' and top != '{'):
                good = False
                break
    print("YES" if good else "NO")
