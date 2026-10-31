"""Page-replacement simulator: FIFO, LRU, OPT (looks into the future, so it is only a yardstick) and CLOCK (second chance)."""
ALGORITHMS = ["FIFO", "LRU", "OPT", "CLOCK"]


def simulate(algorithm, refs, frames):
    algorithm = algorithm.upper()
    if algorithm not in ALGORITHMS:
        raise ValueError(f"unknown algorithm {algorithm}")
    if frames < 1:
        raise ValueError("at least one frame is needed")
    if not refs:
        raise ValueError("empty reference string")
    mem, steps, faults = [], [], 0
    ref_bit, hand = {}, 0                                  # CLOCK state
    last_use = {}                                          # LRU state
    for i, page in enumerate(refs):
        fault, victim = False, None
        if page in mem:
            if algorithm == "CLOCK": ref_bit[page] = 1
        else:
            fault = True; faults += 1
            if len(mem) < frames:
                mem.append(page)
                if algorithm == "CLOCK": ref_bit[page] = 1
            else:
                if algorithm == "FIFO":
                    idx = 0
                elif algorithm == "LRU":
                    idx = min(range(len(mem)), key=lambda k: last_use[mem[k]])
                elif algorithm == "OPT":
                    def next_use(pg):
                        for j in range(i + 1, len(refs)):
                            if refs[j] == pg: return j
                        return len(refs) + 1
                    idx = max(range(len(mem)), key=lambda k: (next_use(mem[k]), -k))
                else:                                      # CLOCK: sweep, clearing reference bits, until a page with bit 0
                    while ref_bit[mem[hand]]:
                        ref_bit[mem[hand]] = 0; hand = (hand + 1) % frames
                    idx = hand; hand = (hand + 1) % frames
                victim = mem[idx]
                if algorithm == "FIFO":
                    mem.pop(0); mem.append(page)
                else:
                    mem[idx] = page
                ref_bit.pop(victim, None)
                if algorithm == "CLOCK": ref_bit[page] = 1
        last_use[page] = i
        steps.append({"step": i + 1, "page": page, "frames": list(mem), "fault": fault, "victim": victim})
    return {"algorithm": algorithm, "frames": frames, "faults": faults, "hits": len(refs) - faults,
            "fault_rate": faults / len(refs), "steps": steps}


def compare(refs, frames, algorithms=None):
    return {a: simulate(a, refs, frames) for a in (algorithms or ALGORITHMS)}
