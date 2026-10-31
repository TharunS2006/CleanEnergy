"""Seeded workload generators, so that every experiment can be repeated exactly."""
import random
from .cpu import Proc


def cpu_workload(n=8, seed=0, kind="mixed", spread=30):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        if kind == "short":
            burst = rng.randint(1, 6)
        elif kind == "long":
            burst = rng.randint(10, 30)
        else:                                            # mixed: mostly short jobs and a few long ones
            burst = rng.randint(1, 5) if rng.random() < 0.7 else rng.randint(10, 30)
        out.append(Proc(f"P{i + 1}", rng.randint(0, spread), burst, rng.randint(1, 5)))
    return out


def page_refs(length=200, pages=20, seed=0, locality=True, set_size=5, phase=40):
    """locality=True: the program works inside a small set of pages for a while (90 % of references), then moves on.
    locality=False: every page is equally likely (the hardest case for any replacement rule)."""
    rng = random.Random(seed)
    if not locality:
        return [rng.randrange(pages) for _ in range(length)]
    refs, hot = [], rng.sample(range(pages), set_size)
    for i in range(length):
        if i and i % phase == 0:
            hot = rng.sample(range(pages), set_size)
        refs.append(rng.choice(hot) if rng.random() < 0.9 else rng.randrange(pages))
    return refs


def disk_requests(n=20, cylinders=200, seed=0, clustered=False):
    rng = random.Random(seed)
    if not clustered:
        reqs = [rng.randrange(cylinders) for _ in range(n)]
    else:                                                # a few busy regions of the disk
        centres = [rng.randrange(cylinders) for _ in range(3)]
        reqs = [min(cylinders - 1, max(0, int(rng.gauss(rng.choice(centres), 8)))) for _ in range(n)]
    return reqs, rng.randrange(cylinders)
