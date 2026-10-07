import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int r = sc.nextInt(), c = sc.nextInt();
        String[] g = new String[r];
        for (int i = 0; i < r; i++) g[i] = sc.next();
        boolean[][] vis = new boolean[r][c];
        int[] dx = {1, -1, 0, 0}, dy = {0, 0, 1, -1};
        int cnt = 0;
        for (int i = 0; i < r; i++)
            for (int j = 0; j < c; j++)
                if (g[i].charAt(j) == '1' && !vis[i][j]) {
                    cnt++;
                    Deque<int[]> q = new ArrayDeque<>();
                    q.add(new int[]{i, j});
                    vis[i][j] = true;
                    while (!q.isEmpty()) {
                        int[] cur = q.poll();
                        for (int d = 0; d < 4; d++) {
                            int nx = cur[0] + dx[d], ny = cur[1] + dy[d];
                            if (nx >= 0 && ny >= 0 && nx < r && ny < c && g[nx].charAt(ny) == '1' && !vis[nx][ny]) {
                                vis[nx][ny] = true;
                                q.add(new int[]{nx, ny});
                            }
                        }
                    }
                }
        System.out.println(cnt);
    }
}
