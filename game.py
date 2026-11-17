"""Logique pure du jeu : aucun accès Discord ni base de données."""
import math
import random

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


def credited_seconds(elapsed: float) -> int:
    """Secondes entières créditées (plafonnées par OFFLINE_CAP)."""
    return int(min(max(elapsed, 0), config.OFFLINE_CAP))


def offline_gain(counts: tuple[int, int, int, int], treelevel: int, elapsed: float) -> int:
    return credited_seconds(elapsed) * production_per_second(counts, treelevel)


_rng = random.SystemRandom()


def spin() -> str:
    """Tire la couleur d'Yggdrasil selon les poids de config.GAMBLING_WEIGHTS."""
    colors = tuple(config.GAMBLING_WEIGHTS)
    return _rng.choices(colors, weights=tuple(config.GAMBLING_WEIGHTS.values()))[0]


def gamble_payout(choice: str, outcome: str, bet: int) -> int:
    """Lucioles rendues au joueur (mise comprise) : 0 si perdu."""
    return bet * config.GAMBLING_PAYOUTS[choice] if choice == outcome else 0


def rebirth_cost(treelevel: int) -> int:
    return config.REBIRTH_BASE * config.REBIRTH_GROWTH ** treelevel
