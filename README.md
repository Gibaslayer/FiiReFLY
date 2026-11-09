**Installation**
 
- pip install -r .\requirements.txt
- ou 
- python3 -m pip install -r .\requirements.txt

**Configuration (`.env`)**

- `DISCORD_TOKEN` : token du bot
- `SITE_ORIGIN` : adresse du site autorisé à lire le classement (ex. `https://monsite.fr`). Par défaut `*`
- `API_PORT` : port de l'API (par défaut `8080`)

**Lancement**

- `python main.py` lance le bot et l'API.

**Commandes**

- `/fenetre` : ouvre ton atelier (capturer, acheter des collecteurs, renaître)
- `/frime` : montre ta progression à tout le monde
- `/classement` : top 10 des joueurs

**API du classement**

`GET /leaderboard?limit=10` (1 à 100, 10 par défaut) renvoie :

```json
[{"name": "pseudo", "fireflies": "123456", "treelevel": 2}]
```

`fireflies` est une chaîne pour ne pas perdre de précision en JavaScript. Le port doit être ouvert, ou placé derrière un reverse proxy.
