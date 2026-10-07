import java.util.*;
import java.io.*;
public class Main {
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        StringTokenizer st = new StringTokenizer(br.readLine());
        int n = Integer.parseInt(st.nextToken()), m = Integer.parseInt(st.nextToken());
        List<List<int[]>> g = new ArrayList<>();
        for (int i = 0; i <= n; i++) g.add(new ArrayList<>());
        for (int i = 0; i < m; i++) {
            st = new StringTokenizer(br.readLine());
            int u = Integer.parseInt(st.nextToken()), v = Integer.parseInt(st.nextToken()), w = Integer.parseInt(st.nextToken());
            g.get(u).add(new int[]{v, w});
            g.get(v).add(new int[]{u, w});
        }
        long INF = Long.MAX_VALUE;
        long[] dist = new long[n + 1];
        Arrays.fill(dist, INF);
        PriorityQueue<long[]> pq = new PriorityQueue<>((a, b) -> Long.compare(a[0], b[0]));
        dist[1] = 0; pq.add(new long[]{0, 1});
        while (!pq.isEmpty()) {
            long[] cur = pq.poll();
            long d = cur[0]; int u = (int) cur[1];
            if (d > dist[u]) continue;
            for (int[] e : g.get(u))
                if (d + e[1] < dist[e[0]]) { dist[e[0]] = d + e[1]; pq.add(new long[]{dist[e[0]], e[0]}); }
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 1; i <= n; i++) sb.append(dist[i] == INF ? -1 : dist[i]).append(i == n ? "\n" : " ");
        System.out.print(sb);
    }
}
