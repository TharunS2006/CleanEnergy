import java.util.*;
public class Main {
    static boolean ok(String s) {
        Deque<Character> st = new ArrayDeque<>();
        for (char c : s.toCharArray()) {
            if (c == '(' || c == '[' || c == '{') st.push(c);
            else {
                char top = st.pop();
                if ((c == ')' && top != '(') || (c == ']' && top != '(') || (c == '}' && top != '{'))
                    return false;
            }
        }
        return true;
    }
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int t = Integer.parseInt(sc.nextLine().trim());
        while (t-- > 0) System.out.println(ok(sc.nextLine().trim()) ? "YES" : "NO");
    }
}
