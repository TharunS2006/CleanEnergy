import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt(), W = sc.nextInt();
        int[] dp = new int[W];
        for (int i = 0; i < n; i++) {
            int v = sc.nextInt(), w = sc.nextInt();
            for (int c = w; c <= W; c++) dp[c] = Math.max(dp[c], dp[c - w] + v);
        }
        System.out.println(dp[W]);
    }
}
