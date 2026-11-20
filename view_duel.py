import discord

import database as db
from view_firefly_fabric import format_number

TIMEOUT = 60


class DuelView(discord.ui.View):
    """Défi pile ou face : l'adversaire accepte ou refuse, le gagnant prend la mise de l'autre."""

    def __init__(self, challenger: discord.Member, opponent: discord.Member, side: str, bet: int):
        super().__init__(timeout=TIMEOUT)
        self.challenger = challenger
        self.opponent = opponent
        self.side = side
        self.other_side = "face" if side == "pile" else "pile"
        self.bet = bet
        self.done = False  # évite qu'un double clic lance deux tirages
        self.interaction: discord.Interaction | None = None

    async def start(self, interaction: discord.Interaction):
        self.interaction = interaction
        embed = discord.Embed(
            title="Pile ou face",
            description=(
                f"{self.challenger.mention} défie {self.opponent.mention} !\n"
                f"Mise : **{format_number(self.bet)}** lucioles chacun.\n"
                f"{self.challenger.display_name} prend **{self.side}**, "
                f"{self.opponent.display_name} prend **{self.other_side}**.\n"
                "Le gagnant remporte la mise de l'autre."
            ),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Réponse attendue dans les {TIMEOUT} secondes.")
        # content=mention : prévient l'adversaire (les mentions dans un embed ne notifient pas)
        await interaction.response.send_message(content=self.opponent.mention, embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.challenger.id, self.opponent.id):
            await interaction.response.send_message("Ce défi ne te concerne pas.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                f"Seul {self.opponent.display_name} peut accepter ce défi.", ephemeral=True
            )
            return
        if self.done:
            await interaction.response.defer()
            return
        self.done = True
        self.stop()
        player, opponent, result = await db.duel(
            self.challenger.id, self.challenger.name, self.opponent.id, self.opponent.name, self.side, self.bet
        )
        await interaction.response.edit_message(content=None, embed=self.result_embed(player, opponent, result), view=None)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        """L'adversaire refuse, ou le challenger annule son défi."""
        if self.done:
            await interaction.response.defer()
            return
        self.done = True
        self.stop()
        action = "refusé" if interaction.user.id == self.opponent.id else "annulé"
        await interaction.response.edit_message(content=None, embed=self.closed_embed(f"Défi {action}"), view=None)

    async def on_timeout(self):
        if self.done or self.interaction is None:
            return
        self.done = True
        await self.interaction.edit_original_response(content=None, embed=self.closed_embed("Défi expiré"), view=None)

    def closed_embed(self, title: str) -> discord.Embed:
        return discord.Embed(title=title, description="Aucune luciole n'a été misée.", color=discord.Color.light_grey())

    def result_embed(self, player: dict, opponent: dict, result: tuple[str, int] | None) -> discord.Embed:
        if result is None:
            poor = player if player["fireflies"] < self.bet else opponent
            return discord.Embed(
                title="Défi annulé",
                description=f"{poor['name']} n'a pas assez de lucioles pour miser {format_number(self.bet)}.",
                color=discord.Color.red(),
            )

        outcome, winner_id = result
        if winner_id == self.challenger.id:
            winner, loser, loser_row = self.challenger, self.opponent, opponent
        else:
            winner, loser, loser_row = self.opponent, self.challenger, player
        embed = discord.Embed(
            title="Pile ou face",
            description=(
                f"La pièce tombe sur **{outcome}** !\n"
                f"{winner.mention} remporte **{format_number(self.bet)}** lucioles de {loser.mention}."
            ),
            color=discord.Color.brand_green(),
        )
        embed.set_footer(
            text=f"{loser.display_name} a perdu {format_number(loser_row['gambling_lost'])} lucioles au gambling au total."
        )
        return embed
