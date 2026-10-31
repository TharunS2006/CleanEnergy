"""Availability mathematics for virtual machines (closed-form results that the simulator is checked against)."""
import math

HOURS_PER_YEAR = 8760.0


def availability(mtbf_hours, mttr_hours):
    """Long-run fraction of time a repairable component is up: MTBF / (MTBF + MTTR). Only the two means matter."""
    if mtbf_hours <= 0 or mttr_hours < 0:
        raise ValueError("MTBF must be positive and MTTR must not be negative")
    return mtbf_hours / (mtbf_hours + mttr_hours)


def downtime_minutes_per_year(a):
    return (1.0 - a) * HOURS_PER_YEAR * 60.0


def nines(a):
    """Number of nines: 0.999 -> 3.0, 0.9999 -> 4.0."""
    return math.inf if a >= 1.0 else -math.log10(1.0 - a)


def series(*parts):
    """All parts must work (a VM needs its host AND its zone AND its region)."""
    out = 1.0
    for p in parts:
        out *= p
    return out


def parallel(*parts):
    """At least one part must work (redundant copies)."""
    out = 1.0
    for p in parts:
        out *= (1.0 - p)
    return 1.0 - out


def k_of_n(k, n, a):
    """At least k of n identical independent parts must work."""
    if not 1 <= k <= n:
        raise ValueError("need 1 <= k <= n")
    return sum(math.comb(n, i) * a ** i * (1 - a) ** (n - i) for i in range(k, n + 1))


def active_passive_unavailability(mtbf, mttr, failover_hours):
    """Exact long-run unavailability of an active-passive pair under exponential failure, repair and failover times (a Markov chain).

    States:  0 both up (the active one serves);  1 standby down;  2 active down, switching to the standby;  3 both down.
    The service is down in states 2 and 3. If the original active instance is repaired during the switch, the switch is abandoned."""
    lam, mu, phi = 1.0 / mtbf, 1.0 / mttr, 1.0 / failover_hours
    q = [[0.0] * 4 for _ in range(4)]
    def rate(i, j, r): q[i][j] += r; q[i][i] -= r
    rate(0, 1, lam); rate(0, 2, lam)
    rate(1, 0, mu); rate(1, 3, lam)
    rate(2, 1, phi); rate(2, 0, mu); rate(2, 3, lam)
    rate(3, 1, mu); rate(3, 2, mu)
    # solve pi Q = 0 with sum(pi) = 1: replace the last balance equation by the normalisation
    a = [[q[j][i] for j in range(4)] for i in range(4)]
    a[3] = [1.0] * 4
    b = [0.0, 0.0, 0.0, 1.0]
    for c in range(4):                                       # Gaussian elimination with partial pivoting
        p = max(range(c, 4), key=lambda r: abs(a[r][c]))
        a[c], a[p] = a[p], a[c]; b[c], b[p] = b[p], b[c]
        for r in range(c + 1, 4):
            f = a[r][c] / a[c][c]
            a[r] = [x - f * y for x, y in zip(a[r], a[c])]; b[r] -= f * b[c]
    pi = [0.0] * 4
    for r in range(3, -1, -1):
        pi[r] = (b[r] - sum(a[r][c] * pi[c] for c in range(r + 1, 4))) / a[r][r]
    return pi[2] + pi[3]


SLA_TABLE = [0.99, 0.995, 0.999, 0.9995, 0.9999, 0.99999]


def sla_downtime(a):
    """Allowed downtime for a target, in minutes per year and per 30-day month."""
    return {"per_year": downtime_minutes_per_year(a), "per_month": (1 - a) * 30 * 24 * 60}
