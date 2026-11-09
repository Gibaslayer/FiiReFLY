import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import api
import config
import database as db
import game
from view_firefly_fabric import View_fabric, format_number

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
site_origin = os.getenv('SITE_ORIGIN', '*')
api_port = int(os.getenv('API_PORT', '8080'))

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.all()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)


async def setup_hook():
    await db.init_db()
    await api.start_api("0.0.0.0", api_port, site_origin)

bot.setup_hook = setup_hook


@bot.tree.command(name="bonjour", description="Répond bonjour à la personne qui l'interpelle")
async def bonjour(interaction: discord.Interaction):
    await interaction.response.send_message(f"Bonjour {interaction.user.mention} !")


@bot.tree.command(name="frime", description="Permet de montrer à tout le monde l'évolution de ton arbre")
async def frime(interaction: discord.Interaction):
    player = await db.get_player(interaction.user.id, interaction.user.name)
    embed = discord.Embed(
        title=f"Frime de {interaction.user.name}",
        description="Ressources totales du joueur :",
        color=discord.Color.gold(),
    )
    embed.add_field(name="Lucioles", value=format_number(player["fireflies"]), inline=False)
    embed.add_field(name="Arbre", value=f"Niveau {player['treelevel']} (x{game.multiplier(player['treelevel'])})", inline=False)
    collectors = "\n".join(
        f"{name} : {format_number(player[column])}"
        for name, column in zip(config.COLLECTOR_NAMES, db.COLLECTOR_COLUMNS)
    )
    embed.add_field(name="Collecteurs", value=collectors, inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="classement", description="Affiche les 10 joueurs ayant le plus de lucioles")
async def classement(interaction: discord.Interaction):
    rows = await db.get_leaderboard(10)
    lines = [
        f"**{i}.** {row['name']} : {format_number(row['fireflies'])} lucioles (arbre niveau {row['treelevel']})"
        for i, row in enumerate(rows, start=1)
    ]
    embed = discord.Embed(
        title="Classement",
        description="\n".join(lines) or "Aucun joueur pour l'instant.",
        color=discord.Color.gold(),
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="fenetre", description="Ouvre ton atelier de lucioles")
async def fenetre(interaction: discord.Interaction):
    view = View_fabric(interaction.user.id, interaction.user.name)
    await view.start(interaction)


@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"{bot.user.name} is ready to use with {len(synced)} commands")


bot.run(token, log_handler=handler, log_level=logging.DEBUG)
