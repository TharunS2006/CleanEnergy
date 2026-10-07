import java.util.*;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt(), m = sc.nextInt();
        List<List<Integer>> g = new ArrayList<>();
        for (int i = 0; i <= n; i++) g.add(new ArrayList<>());
        int[] indeg = new int[n + 1];
        for (int i = 0; i < m; i++) {
            int u = sc.nextInt(), v = sc.nextInt();
            g.get(u).add(v);
            indeg[v]++;
        }
        Deque<Integer> q = new ArrayDeque<>();
        for (int i = 1; i <= n; i++) if (indeg[i] == 0) q.push(i);
        List<Integer> order = new ArrayList<>();
        while (!q.isEmpty()) {
            int u = q.pop();
            order.add(u);
            for (int v : g.get(u)) if (--indeg[v] == 0) q.push(v);
        }
        StringBuilder sb = new StringBuilder();
        for (int x : order) sb.append(x).append(' ');
        System.out.println(sb.toString().trim());
    }
}
