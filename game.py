"""Logique pure du jeu : aucun accès Discord ni base de données."""
import math

import config


def multiplier(treelevel: int) -> int:
    return 1 + treelevel


def click_gain(treelevel: int) -> int:
    return multiplier(treelevel)


def collector_cost(index: int, owned: int) -> int:
    return math.ceil(config.COLLECTOR_BASE_COSTS[index] * config.COST_GROWTH ** owned)


def production_per_second(counts: tuple[int, int, int, int], treelevel: int) -> int:
    base = sum(n * rate for n, rate in zip(counts, config.COLLECTOR_RATES))
    return base * multiplier(treelevel)


def offline_gain(counts: tuple[int, int, int, int], treelevel: int, elapsed: float) -> int:
    seconds = min(max(elapsed, 0), config.OFFLINE_CAP)
    return int(seconds) * production_per_second(counts, treelevel)


def rebirth_cost(treelevel: int) -> int:
    return config.REBIRTH_BASE * config.REBIRTH_GROWTH ** treelevel
