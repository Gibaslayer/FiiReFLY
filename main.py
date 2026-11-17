import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import api
import config
import database as db
import game
from view_firefly_fabric import View_fabric, format_number
from view_gambling import GamblingView

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
site_origin = os.getenv('SITE_ORIGIN', '*')
api_port = int(os.getenv('API_PORT', '8080'))

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()

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


@bot.tree.command(name="classement", description="Affiche les 10 joueurs ayant le plus haut niveau d'arbre et le plus de lucioles")
async def classement(interaction: discord.Interaction):
    rows = await db.get_leaderboard(10)
    lines = [
        f"**{i}.**" + discord.utils.escape_markdown(f" {row['name']} : {format_number(row['fireflies'])} lucioles (arbre niveau {row['treelevel']})")
        for i, row in enumerate(rows, start=1)
    ]
    embed = discord.Embed(
        title="Classement",
        description="\n".join(lines) or "Aucun joueur pour l'instant.",
        color=discord.Color.gold(),
    )
    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="classement_lucioles", description="Affiche les 10 joueurs ayant le plus de lucioles")
async def classement_lucioles(interaction: discord.Interaction):
    rows = await db.get_leaderboard(10, by_tree_level=False)
    lines = [
        f"**{i}.**" + discord.utils.escape_markdown(f" {row['name']} : {format_number(row['fireflies'])} lucioles (arbre niveau {row['treelevel']})")
        for i, row in enumerate(rows, start=1)
    ]
    embed = discord.Embed(
        title="Classement",
        description="\n".join(lines) or "Aucun joueur pour l'instant.",
        color=discord.Color.gold(),
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="game", description="Ouvre ton atelier de lucioles")
async def open_game(interaction: discord.Interaction):
    view = View_fabric(interaction.user.id, interaction.user.name)
    await view.start(interaction)


@bot.tree.command(name="gambling", description="Parie des lucioles à Yggdrasil sur une couleur (rouge, noir ou vert)")
@app_commands.describe(couleur="La couleur sur laquelle tu paries", mise="Nombre de lucioles à parier à Yggdrasil")
@app_commands.choices(couleur=[
    app_commands.Choice(name="Rouge (x2)", value="rouge"),
    app_commands.Choice(name="Noir (x2)", value="noir"),
    app_commands.Choice(name="Vert (x36)", value="vert"),
])
async def gambling(interaction: discord.Interaction, couleur: app_commands.Choice[str], mise: app_commands.Range[int, 1]):
    player = await db.get_player(interaction.user.id, interaction.user.name)
    if player["fireflies"] < mise:
        await interaction.response.send_message(
            f"Tu n'as que **{format_number(player['fireflies'])}** lucioles : impossible d'en parier {format_number(mise)}.",
            ephemeral=True,
        )
        return
    view = GamblingView(interaction.user.id, interaction.user.name, couleur.value, mise)
    await view.start(interaction)


@bot.tree.command(name="help",description="Liste toutes les commandes du bot")
async def help_command(interaction: discord.Interaction):
    # Générée depuis les commandes enregistrées : une nouvelle commande apparaît toute seule.
    lines = [
        f"**/{command.name}** : {command.description}"
        for command in sorted(bot.tree.get_commands(), key=lambda c: c.name)
    ]
    embed = discord.Embed(
        title="Commandes disponibles",
        description="\n".join(lines),
        color=discord.Color.gold(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"{bot.user.name} is ready to use with {len(synced)} commands")


bot.run(token, log_handler=handler, log_level=logging.DEBUG)
