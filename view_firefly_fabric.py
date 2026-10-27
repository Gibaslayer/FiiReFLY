import discord
import database as db


collectors_names = ("Filet(s) de capture", "Lasso(s) à lucioles", "Catapulte(s) à filets", "Essaim(s) de drones à filets")
collectors_names_singular = ("Filet de capture", "Lasso à lucioles", "Catapulte à filets", "Essaim de drones à filets")
collectors_buff = (1, 10, 100, 1000)

class View_fabric(discord.ui.View):
    def __init__(self, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.page = "accueil"

    def get_embed(self) -> discord.Embed:
        if self.page == "accueil":
            embed = discord.Embed(
                title="FiiReFLY Fabric : Accueil",
                description="Bienvenue dans votre atelier de lucioles !\nCliquez sur les boutons ci-dessous pour vous déplacer.",
                color=discord.Color.dark_theme()
            )
            embed.add_field(name="État", value="En attente d'ordres", inline=False)
        elif self.page == "atelier":
            embed = discord.Embed(
                title="FiiReFLY Fabric : Atelier",
                description="Ici, vous capturez et traitez les lucioles.",
                color=discord.Color.gold()
            )
            embed.add_field(name="Action disponible", value="Filets prêts au déploiement.", inline=False)
        elif self.page == "arbre":
                    embed = discord.Embed(
                        title="FiiReFLY Fabric : Arbre de la vie",
                        description="Améliorez votre arbre pour attirer naturellement plus de lucioles dans votre jardin.",
                        color=discord.Color.gold()
                    )
                    embed.add_field(name="Action disponible", value="Filets prêts au déploiement.", inline=False)
        elif self.page == "boutique":
            embed = discord.Embed(
                title="FiiReFLY Fabric : Boutique",
                description="Achetez des améliorations pour automatiser la récolte.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Matériel", value=f"""
                            {collectors_names_singular[0]} ({collectors_buff[0]}/s) : 15 lucioles 
                            Possédés : 
                            {collectors_names_singular[1]} ({collectors_buff[1]}/s) : 1 000 lucioles
                            Possédés : 
                            {collectors_names_singular[2]} ({collectors_buff[2]}/s) : 100 000 lucioles
                            Possédés : 
                            {collectors_names_singular[3]} ({collectors_buff[3]}/s) : 10 000 000 lucioles
                            Possédés : 
                            """, inline=False)
        return embed

    @discord.ui.button(label="Accueil", style=discord.ButtonStyle.primary, row=0)
    async def btn_accueil(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = "accueil"
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Atelier", style=discord.ButtonStyle.secondary, row=0)
    async def btn_atelier(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = "atelier"
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Boutique", style=discord.ButtonStyle.secondary, row=0)
    async def btn_boutique(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = "boutique"
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
        
    @discord.ui.button(label="Arbre", style=discord.ButtonStyle.primary, row=0)
    async def btn_arbre(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.page = "arbre"
            await interaction.response.edit_message(embed=self.get_embed(), view=self)