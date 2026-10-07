import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String s = sc.next(), t = sc.next();
        int n = s.length(), m = t.length();
        int[][] dp = new int[n][m];
        for (int i = 1; i <= n; i++)
            for (int j = 1; j <= m; j++) {
                int cost = (s.charAt(i) == t.charAt(j)) ? 1 : 0;
                dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i - 1][j - 1] + cost);
            }
        System.out.println(dp[n][m]);
    }
}
