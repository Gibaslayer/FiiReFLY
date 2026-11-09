"""API publique en lecture seule du classement."""
from aiohttp import web

import database as db

DEFAULT_LIMIT = 10
MAX_LIMIT = 100


def build_app(origin: str) -> web.Application:
    @web.middleware
    async def cors(request: web.Request, handler):
        response = await handler(request)
        response.headers["Access-Control-Allow-Origin"] = origin
        return response

    async def leaderboard(request: web.Request) -> web.Response:
        try:
            limit = int(request.query.get("limit", DEFAULT_LIMIT))
        except ValueError:
            return web.json_response({"error": "limit doit être un entier"}, status=400)
        limit = max(1, min(limit, MAX_LIMIT))
        rows = await db.get_leaderboard(limit)
        # fireflies en chaîne 
        return web.json_response([
            {"name": row["name"], "fireflies": str(row["fireflies"]), "treelevel": row["treelevel"]}
            for row in rows
        ])

    app = web.Application(middlewares=[cors])
    app.router.add_get("/leaderboard", leaderboard)
    return app


async def start_api(host: str, port: int, origin: str) -> web.AppRunner:
    runner = web.AppRunner(build_app(origin))
    await runner.setup()
    await web.TCPSite(runner, host, port).start()
    return runner
