"""Backups: how much data is lost (RPO) and how long a restore takes (RTO)."""
import random


def mean_data_age_minutes(interval_minutes, success_probability=1.0):
    """Average age of the newest good backup at a random moment: half an interval plus the intervals lost to failed backups.
    mean = interval * (1/p - 1/2)."""
    if interval_minutes <= 0 or not 0 < success_probability <= 1:
        raise ValueError("interval must be positive and 0 < p <= 1")
    return interval_minutes * (1.0 / success_probability - 0.5)


def percentile_data_age_minutes(interval_minutes, success_probability, q=0.99):
    """Age that is exceeded with probability 1 - q. With p = 1 the worst case is one interval."""
    import math
    if success_probability >= 1.0:
        return interval_minutes
    k = math.ceil(math.log(1 - q) / math.log(1 - success_probability))      # failed backups in a row that happen with probability 1 - q
    return interval_minutes * (k + 1)


def restore_minutes(size_gb, throughput_mb_s, boot_minutes=20.0, check_minutes=10.0):
    """Time to bring a VM back from a backup: copy the data, boot the VM, check the service."""
    if size_gb <= 0 or throughput_mb_s <= 0:
        raise ValueError("size and throughput must be positive")
    copy = size_gb * 1024.0 / throughput_mb_s / 60.0
    return copy + boot_minutes + check_minutes


def simulate_data_age(interval_minutes, success_probability, trials=200000, seed=1):
    """Monte Carlo check of the mean: pick a random moment, find the newest successful backup."""
    rng = random.Random(seed)
    ages = []
    for _ in range(trials):
        age = rng.uniform(0, interval_minutes)
        while rng.random() > success_probability:
            age += interval_minutes
        ages.append(age)
    return sum(ages) / len(ages)
