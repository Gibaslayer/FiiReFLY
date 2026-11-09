"""Constantes d'équilibrage du jeu."""

COLLECTOR_NAMES = ("Filet(s) de capture", "Lasso(s) à lucioles", "Catapulte(s) à filets", "Essaim(s) de drones à filets")
COLLECTOR_NAMES_SINGULAR = ("Filet de capture", "Lasso à lucioles", "Catapulte à filets", "Essaim de drones à filets")

COLLECTOR_BASE_COSTS = (15, 1_000, 100_000, 10_000_000)
COLLECTOR_RATES = (1, 10, 100, 1000)  # lucioles par seconde et par collecteur
COST_GROWTH = 1.15                    # le prix est multiplié par 1,15 à chaque exemplaire possédé

CLICK_COOLDOWN = 1.0                  # secondes minimum entre deux clics
OFFLINE_CAP = 8 * 3600                # production hors ligne plafonnée à 8 h

REBIRTH_BASE = 1_000_000              # coût du niveau 0 -> 1
REBIRTH_GROWTH = 5                    # le coût est multiplié par 5 à chaque niveau

MAX_FIREFLIES = 2**63 - 1             # limite des entiers SQLite
