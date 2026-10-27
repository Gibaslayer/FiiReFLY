import math
import time
import aiosqlite

DB_NAME = "firefly.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                fireflies INTEGER DEFAULT 0,
                collectors INTEGER DEFAULT 0,
                collectorsv2 INTEGER DEFAULT 0,
                collectorsv3 INTEGER DEFAULT 0,
                collectorsv4 INTEGER DEFAULT 0,
                multiplicator INTEGER DEFAULT 1,
                treelevel INTEGER DEFAULT 0,
                last_collected REAL,
                last_manual_click REAL DEFAULT 0
            )
        """)
        await db.commit()

async def get_player(user_id: int) -> dict:
    now = time.time()
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()

        if row is None:
            await db.execute(
                "INSERT INTO players (user_id, fireflies, collectors, last_collected, last_manual_click) VALUES (?, 0, 0, ?, 0)",
                (user_id, now)
            )
            await db.commit()
            return {
                "user_id": user_id,
                "fireflies": 0,
                "last_collected": now,
                "last_manual_click": 0,
                "collectors": 0,
                "collectorsv2": 0,
                "collectorsv3": 0,
                "collectorsv4": 0,
                "multiplicator": 1,
                "treelevel": 0
            }

        data = dict(row)
        # Production passive des collecteurs (1 luciole par collecteur par seconde)
        elapsed = int(now - data["last_collected"])
        if elapsed > 0 and (data["collectors"]+data["collectorsv2"]+data["collectorsv3"]+data["collectorsv4"] > 0):
            data["fireflies"] += (
                    (10 ** data["treelevel"]) * elapsed * data["multiplicator"] * 
                    ( data["collectors"] if data["collectors"] > 0 else 1) *
                    ( data["collectorsv2"] if data["collectorsv2"] > 0 else 1) *
                    ( data["collectorsv3"] if data["collectorsv3"] > 0 else 1) *
                    ( data["collectorsv4"] if data["collectorsv4"] > 0 else 1)
                )
        data["last_collected"] = now

        await db.execute(
            "UPDATE players SET fireflies = ?, last_collected = ? WHERE user_id = ?",
            (data["fireflies"], data["last_collected"], user_id)
        )
        await db.commit()
        return data

async def save_player(data: dict):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE players
            SET fireflies = ?, collectors = ?, collectorsv2 = 0, collectorsv3 = 0, collectorsv4 = 0,  multiplicator = 0,  treelevel = 0, last_collected = ?, last_manual_click = ?, 
            WHERE user_id = ?
        """, (data["fireflies"], data["collectors"], data["collectorsv2"], data["collectorsv3"], data["collectorsv4"], data["multiplicator"], data["treelevel"], data["last_collected"], data["last_manual_click"], data["user_id"]))
        await db.commit()