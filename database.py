import time
from contextlib import asynccontextmanager

import aiosqlite

import config
import game

DB_NAME = "firefly.db"
TIMEOUT = 10  # secondes d'attente si la base est occupée

COLLECTOR_COLUMNS = ("collectors", "collectorsv2", "collectorsv3", "collectorsv4")


async def init_db():
    async with aiosqlite.connect(DB_NAME, timeout=TIMEOUT) as db:
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
                last_updated REAL DEFAULT 0,               
                last_manual_click REAL NOT NULL DEFAULT 0
            )
        """)
        #last_collected : La dernière fois que le joueur s'est connecté activement
        #last_updated : La dernière fois que le classement a mis à jour ses gains en arrière-plan
        await db.commit()
        
async def maj_lucioles():
    now = time.time()
    async with aiosqlite.connect(DB_NAME, timeout=TIMEOUT) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        
        # Récupérer tous les joueurs
        async with db.execute("SELECT * FROM players") as cursor:
            rows = await cursor.fetchall()
            
        for row in rows:
            player = dict(row)
            user_id = player["user_id"]
            
            # On utilise last_updated s'il existe et est valide (> 0), sinon last_collected
            ref_time = player["last_updated"] if player["last_updated"] and player["last_updated"] > 0 else player["last_collected"]
            time_delta = now - ref_time
            
            if time_delta <= 0:
                continue
                
            # Calcul du gain basé sur l'intervalle depuis la dernière mise à jour auto
            gain = game.offline_gain(_counts(player), player["treelevel"], time_delta)
            player["fireflies"] = min(player["fireflies"] + gain, config.MAX_FIREFLIES)
            
            # Mise à jour UNIQUEMENT des fireflies et de last_updated.
            # last_collected n'est PAS touché pour préserver la limite de la collecte hors-ligne du joueur.
            await db.execute(
                "UPDATE players SET fireflies = ?, last_updated = ? WHERE user_id = ?",
                (player["fireflies"], now, user_id)
            )
            
        await db.commit()


def _counts(player: dict) -> tuple[int, int, int, int]:
    return tuple(player[column] for column in COLLECTOR_COLUMNS)


@asynccontextmanager
async def _transaction(user_id: int, name: str):
    """Une opération = une transaction : lecture, production hors ligne, écriture.

    Une opération concurrente attend la fin de celle-ci et repart de l'état à jour.
    """
    now = time.time()
    async with aiosqlite.connect(DB_NAME, timeout=TIMEOUT) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "INSERT OR IGNORE INTO players (user_id, name, last_collected, last_updated) VALUES (?, ?, ?, ?)",
            (user_id, name, now, now),
        )
        async with db.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cursor:
            player = dict(await cursor.fetchone())
            
        # On prend le plus récent entre la dernière collecte active et la dernière maj du classement
        ref_time = max(player["last_collected"], player["last_updated"])
        time_delta = now - ref_time

        gain = game.offline_gain(_counts(player), player["treelevel"], time_delta)
        player["fireflies"] = min(player["fireflies"] + gain, config.MAX_FIREFLIES)
        player["last_collected"] = now
        player["last_updated"] = now
        player["name"] = name

        yield player

        await db.execute(
            """UPDATE players SET name = ?, fireflies = ?, collectors = ?, collectorsv2 = ?,
               collectorsv3 = ?, collectorsv4 = ?, treelevel = ?, last_collected = ?, last_updated = ?,
               last_manual_click = ? WHERE user_id = ?""",
            (player["name"], player["fireflies"], *_counts(player), player["treelevel"],
             player["last_collected"], player["last_updated"], player["last_manual_click"], user_id),
        )
        await db.commit()


async def get_player(user_id: int, name: str) -> dict:
    async with _transaction(user_id, name) as player:
        return player


async def click(user_id: int, name: str) -> tuple[dict, bool]:
    async with _transaction(user_id, name) as player:
        now = player["last_collected"]
        if now - player["last_manual_click"] < config.CLICK_COOLDOWN:
            return player, False
        player["fireflies"] = min(player["fireflies"] + game.click_gain(player["treelevel"]), config.MAX_FIREFLIES)
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


async def rebirth(user_id: int, name: str) -> tuple[dict, bool]:
    async with _transaction(user_id, name) as player:
        if player["fireflies"] < game.rebirth_cost(player["treelevel"]):
            return player, False
        player["fireflies"] = 0
        for column in COLLECTOR_COLUMNS:
            player[column] = 0
        player["treelevel"] += 1
        return player, True


async def get_leaderboard(limit: int, byTreeLvl:bool = True) -> list[dict]:
    await maj_lucioles();
    async with aiosqlite.connect(DB_NAME, timeout=TIMEOUT) as db:
        db.row_factory = aiosqlite.Row
        if (byTreeLvl) :
            async with db.execute(
                        "SELECT name, fireflies, treelevel FROM players ORDER BY treelevel DESC, fireflies DESC LIMIT ?", (limit,)
                    ) as cursor:
                        return [dict(row) for row in await cursor.fetchall()]
        else :
            async with db.execute(
                "SELECT name, fireflies, treelevel FROM players ORDER BY fireflies DESC LIMIT ?", (limit,)
            ) as cursor:
                return [dict(row) for row in await cursor.fetchall()]
