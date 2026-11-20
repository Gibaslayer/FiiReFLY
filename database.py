import time
from contextlib import asynccontextmanager

import aiosqlite

import config
import game

DB_NAME = "firefly.db"
TIMEOUT = 10  # secondes d'attente si la base est occupée

COLLECTOR_COLUMNS = ("collectors", "collectorsv2", "collectorsv3", "collectorsv4")

# Colonnes ajoutées après la première version : on les ajoute aux anciennes bases au démarrage.
NEW_COLUMNS = {
    "click_upgrades": "INTEGER NOT NULL DEFAULT 0",
    "gambling_lost": "INTEGER NOT NULL DEFAULT 0",  # total des lucioles perdues en pariant
    "gambling_won": "INTEGER NOT NULL DEFAULT 0",  # total des lucioles gagnées en pariant (gains nets)
}


async def init_db():
    async with aiosqlite.connect(DB_NAME, timeout=TIMEOUT) as db:
        # last_collected : instant jusqu'auquel la production du joueur a été créditée.
        # (Les anciennes bases peuvent avoir une colonne last_updated : elle n'est plus utilisée.)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                fireflies INTEGER NOT NULL DEFAULT 0,
                collectors INTEGER NOT NULL DEFAULT 0,
                collectorsv2 INTEGER NOT NULL DEFAULT 0,
                collectorsv3 INTEGER NOT NULL DEFAULT 0,
                collectorsv4 INTEGER NOT NULL DEFAULT 0,
                treelevel INTEGER NOT NULL DEFAULT 0,
                last_collected REAL NOT NULL,
                last_manual_click REAL NOT NULL DEFAULT 0,
                click_upgrades INTEGER NOT NULL DEFAULT 0,
                gambling_lost INTEGER NOT NULL DEFAULT 0,
                gambling_won INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.commit()


def _counts(player: dict) -> tuple[int, int, int, int]:
    return tuple(player[column] for column in COLLECTOR_COLUMNS)


async def _load_player(db, user_id: int, name: str, now: float) -> dict:
    """Lit la fiche du joueur (la crée si besoin) et y ajoute la production depuis sa dernière visite.

    player["now"] est l'instant de l'opération (non enregistré).
    """
    await db.execute(
        "INSERT OR IGNORE INTO players (user_id, name, last_collected) VALUES (?, ?, ?)",
        (user_id, name, now),
    )
    async with db.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cursor:
        player = dict(await cursor.fetchone())

    elapsed = now - player["last_collected"]
    seconds = game.credited_seconds(elapsed)
    gain = seconds * game.production_per_second(_counts(player), player["treelevel"])
    player["fireflies"] = min(player["fireflies"] + gain, config.MAX_FIREFLIES)
    # On n'avance que des secondes entières créditées : la fraction restante
    # n'est pas perdue. Au-delà du plafond hors ligne, l'excédent est abandonné.
    player["last_collected"] = now if elapsed > config.OFFLINE_CAP else player["last_collected"] + seconds
    player["name"] = name
    player["now"] = now
    return player


async def _save_player(db, player: dict):
    await db.execute(
        """UPDATE players SET name = ?, fireflies = ?, collectors = ?, collectorsv2 = ?,
           collectorsv3 = ?, collectorsv4 = ?, treelevel = ?, last_collected = ?,
           last_manual_click = ?, click_upgrades = ?, gambling_lost = ?,
           gambling_won = ? WHERE user_id = ?""",
        (player["name"], player["fireflies"], *_counts(player), player["treelevel"],
         player["last_collected"], player["last_manual_click"], player["click_upgrades"],
         player["gambling_lost"], player["gambling_won"], player["user_id"]),
    )


@asynccontextmanager
async def _transaction(user_id: int, name: str):
    """Une opération = une transaction : lecture, production hors ligne, écriture.

    Une opération concurrente attend la fin de celle-ci et repart de l'état à jour.
    """
    now = time.time()
    async with aiosqlite.connect(DB_NAME, timeout=TIMEOUT) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        player = await _load_player(db, user_id, name, now)
        yield player
        await _save_player(db, player)
        await db.commit()


async def get_player(user_id: int, name: str) -> dict:
    async with _transaction(user_id, name) as player:
        return player


async def click(user_id: int, name: str) -> tuple[dict, bool]:
    async with _transaction(user_id, name) as player:
        now = player["now"]
        if now - player["last_manual_click"] < config.CLICK_COOLDOWN:
            return player, False
        gain = game.click_gain(player["treelevel"], _counts(player), player["click_upgrades"])
        player["fireflies"] = min(player["fireflies"] + gain, config.MAX_FIREFLIES)
        player["last_manual_click"] = now
        return player, True


async def buy_collector(user_id: int, name: str, index: int) -> tuple[dict, bool]:
    async with _transaction(user_id, name) as player:
        column = COLLECTOR_COLUMNS[index]
        cost = game.collector_cost(index, player[column])
        if player["fireflies"] < cost:
            return player, False
        player["fireflies"] -= cost
        player[column] += 1
        return player, True


async def buy_click_upgrade(user_id: int, name: str) -> tuple[dict, bool]:
    async with _transaction(user_id, name) as player:
        cost = game.click_upgrade_cost(player["click_upgrades"])
        if player["fireflies"] < cost:
            return player, False
        player["fireflies"] -= cost
        player["click_upgrades"] += 1
        return player, True


async def rebirth(user_id: int, name: str) -> tuple[dict, bool]:
    async with _transaction(user_id, name) as player:
        if player["fireflies"] < game.rebirth_cost(player["treelevel"]):
            return player, False
        player["fireflies"] = 0
        for column in COLLECTOR_COLUMNS:
            player[column] = 0
        player["click_upgrades"] = 0
        player["treelevel"] += 1
        return player, True


async def gamble(user_id: int, name: str, choice: str, bet: int) -> tuple[dict, tuple[str, int] | None]:
    """Pari sur une couleur. Renvoie (joueur, (couleur tirée, lucioles rendues)),
    ou (joueur, None) si le solde est insuffisant. Tirage et paiement sont dans la
    même transaction que la vérification du solde."""
    async with _transaction(user_id, name) as player:
        if bet < 1 or player["fireflies"] < bet:
            return player, None
        outcome = game.spin()
        payout = game.gamble_payout(choice, outcome, bet)
        player["fireflies"] = min(player["fireflies"] - bet + payout, config.MAX_FIREFLIES)
        if payout == 0:
            player["gambling_lost"] += bet
        else:
            player["gambling_won"] += payout - bet  # gain net
        return player, (outcome, payout)


async def duel(user_id: int, name: str, opponent_id: int, opponent_name: str,
               side: str, bet: int) -> tuple[dict, dict, tuple[str, int] | None]:
    """Pile ou face entre deux joueurs : le gagnant prend la mise de l'autre.

    `side` est le côté choisi par `user_id` (l'adversaire a l'autre). Renvoie
    (joueur, adversaire, (côté tiré, id du gagnant)), ou None à la place du résultat
    si l'un des deux n'a pas assez de lucioles. Les deux fiches sont modifiées
    dans la même transaction.
    """
    if user_id == opponent_id:
        raise ValueError("On ne peut pas se défier soi-même")
    now = time.time()
    async with aiosqlite.connect(DB_NAME, timeout=TIMEOUT) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        player = await _load_player(db, user_id, name, now)
        opponent = await _load_player(db, opponent_id, opponent_name, now)

        result = None
        if bet >= 1 and player["fireflies"] >= bet and opponent["fireflies"] >= bet:
            outcome = game.coin_flip()
            winner, loser = (player, opponent) if outcome == side else (opponent, player)
            winner["fireflies"] = min(winner["fireflies"] + bet, config.MAX_FIREFLIES)
            loser["fireflies"] -= bet
            loser["gambling_lost"] += bet
            winner["gambling_won"] += bet
            result = (outcome, winner["user_id"])

        await _save_player(db, player)
        await _save_player(db, opponent)
        await db.commit()
    return player, opponent, result


async def _ranked(by_tree_level: bool) -> list[dict]:
    """Tous les joueurs triés. Lecture seule : les lucioles incluent la production
    en cours (calculée à la volée), sans rien écrire dans la base."""
    now = time.time()
    async with aiosqlite.connect(DB_NAME, timeout=TIMEOUT) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM players") as cursor:
            players = [dict(row) for row in await cursor.fetchall()]

    rows = []
    for player in players:
        gain = game.offline_gain(_counts(player), player["treelevel"], now - player["last_collected"])
        rows.append({
            "user_id": player["user_id"],
            "name": player["name"],
            "fireflies": min(player["fireflies"] + gain, config.MAX_FIREFLIES),
            "treelevel": player["treelevel"],
        })

    if by_tree_level:
        rows.sort(key=lambda r: (r["treelevel"], r["fireflies"]), reverse=True)
    else:
        rows.sort(key=lambda r: r["fireflies"], reverse=True)
    return rows


def _public(row: dict) -> dict:
    return {key: row[key] for key in ("name", "fireflies", "treelevel")}


async def get_leaderboard(limit: int, by_tree_level: bool = True) -> list[dict]:
    return [_public(row) for row in (await _ranked(by_tree_level))[:limit]]


async def get_leaderboard_for(user_id: int, limit: int, by_tree_level: bool = True) -> tuple[list[dict], dict | None]:
    """Top `limit` + la ligne du joueur (avec son "rank"), ou None s'il n'a jamais joué."""
    ranked = await _ranked(by_tree_level)
    me = next(
        ({**_public(row), "rank": rank} for rank, row in enumerate(ranked, start=1) if row["user_id"] == user_id),
        None,
    )
    return [_public(row) for row in ranked[:limit]], me
