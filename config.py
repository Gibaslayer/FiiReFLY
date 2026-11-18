"""Constantes d'équilibrage du jeu."""

COLLECTOR_NAMES = ("Filet(s) de capture", "Lasso(s) à lucioles", "Catapulte(s) à filets", "Essaim(s) de drones à filets")
COLLECTOR_NAMES_SINGULAR = ("Filet de capture", "Lasso à lucioles", "Catapulte à filets", "Essaim de drones à filets")

COLLECTOR_BASE_COSTS = (15, 1_000, 100_000, 10_000_000)
COLLECTOR_RATES = (1, 10, 100, 1000)  # lucioles par seconde et par collecteur
COST_GROWTH = 1.15                    # le prix est multiplié par 1,15 à chaque exemplaire possédé

MILESTONE_STEP = 25                   # à chaque multiple de 25 collecteurs d'un type, sa production double

CLICK_UPGRADE_BASE_COST = 5_000       # amélioration de clic : prix du premier niveau
CLICK_UPGRADE_GROWTH = 1.5            # le prix est multiplié par 1,5 à chaque niveau possédé
CLICK_UPGRADE_RATIO = 10              # chaque niveau ajoute 1/10 (0,1x) de la production par seconde à chaque clic

CLICK_COOLDOWN = 1.0                 # secondes minimum entre deux clics
OFFLINE_CAP = 8 * 3600                # production hors ligne plafonnée à 8 h

REBIRTH_BASE = 1_000_000              # coût du niveau 0 -> 1
REBIRTH_GROWTH = 5                    # le coût est multiplié par 5 à chaque niveau

MAX_FIREFLIES = 2**63 - 1             # limite des entiers SQLite

# Pari à Yggdrasil (roulette à 37 cases : 18 rouges, 18 noires, 1 verte)
GAMBLING_WEIGHTS = {"rouge": 18, "noir": 18, "vert": 1}
GAMBLING_PAYOUTS = {"rouge": 2, "noir": 2, "vert": 36}  # multiple de la mise rendu en cas de gain
