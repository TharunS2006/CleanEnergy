import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt(), W = sc.nextInt();
        long[] dp = new long[W + 1];
        for (int i = 0; i < n; i++) {
            int w = sc.nextInt();
            long v = sc.nextLong();
            for (int c = W; c >= w; c--) dp[c] = Math.max(dp[c], dp[c - w] + v);
        }
        System.out.println(dp[W]);
    }
}
