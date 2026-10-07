import java.util.*;
public class Main {
    public static void main(String[] args) {
        String s = new Scanner(System.in).next();
        int[] last = new int[128];
        Arrays.fill(last, -1);
        int left = 0, best = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (last[c] >= left) left = last[c] + 1;
            last[c] = i;
            best = Math.max(best, i - left + 1);
        }
        System.out.println(best);
    }
}
