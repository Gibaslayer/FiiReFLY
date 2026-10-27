import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from view_firefly_fabric import View_fabric
from view_firefly_fabric import collectors_names
import database as db

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.all()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.tree.command(name="bonjour", description="Répond bonjour à la personne qui l'interpelle")
async def bonjour(interaction: discord.Interaction):
    await interaction.response.send_message(f"Bonjour {interaction.user.mention} !")
    
@bot.tree.command(name="frime", description="Permet de montrer à tout le monde l'évolution de ton arbre")    
async def frime(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"Frime de {interaction.user.name}",
        description="Ressources totales du joueur :",
        color=discord.Color.blue()
    )
    data_user = await db.get_player(interaction.user.id)
    embed.add_field(name="Lucioles", value=f"Nombre de lucioles : {data_user["fireflies"]}", inline=False)
    embed.add_field(name="Arbre", value=f"Niveau de l'arbre : {data_user["treelevel"]}", inline=False)  
    embed.add_field(name="Multiplicateur", value=f"Multiplicateur : {data_user["multiplicator"]}", inline=False)
    embed.add_field(name="Collecteurs", value=f"{collectors_names[0]} : {data_user["collectors"]}\n{collectors_names[1]} : {data_user["collectorsv2"]}\n{collectors_names[2]} : {data_user["collectorsv3"]}\n{collectors_names[3]} : {data_user["collectorsv4"]}", inline=False)
    
    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="fenetre", description="Lance la fenetre de test")    
async def fenetre(interaction: discord.Interaction):
    view = View_fabric()
    await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)
        
@bot.event
async def on_ready():
    await db.init_db()
    synced = await bot.tree.sync()
    print(f"{bot.user.name} is ready to use with {len(synced)} commands")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)