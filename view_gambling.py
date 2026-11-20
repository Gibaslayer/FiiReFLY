import discord

import config
import database as db
from view_firefly_fabric import format_number

EMOJIS = {"rouge": "🔴", "noir": "⚫", "vert": "🟢"}
TIMEOUT = 60


def _label(color: str) -> str:
    return f"{EMOJIS[color]} {color.capitalize()}"


def confirm_embed(color: str, bet: int) -> discord.Embed:
    total = sum(config.GAMBLING_WEIGHTS.values())
    chance = config.GAMBLING_WEIGHTS[color] / total * 100
    payout = config.GAMBLING_PAYOUTS[color]
    embed = discord.Embed(
        title="Pari à Yggdrasil",
        description=(
            f"Tu vas parier **{format_number(bet)}** lucioles sur **{_label(color)}**.\n"
            f"Si tu gagnes, tu reçois **{format_number(bet * payout)}** lucioles (x{payout}). "
            f"Sinon, ta mise est perdue.\n"
            f"Chance de gagner : **{chance:.1f} %**"
        ),
        color=discord.Color.gold(),
    )
    embed.set_footer(text=f"Confirme dans les {TIMEOUT} secondes.")
    return embed


def result_embed(color: str, bet: int, player: dict, result: tuple[str, int] | None) -> discord.Embed:
    if result is None:
        return discord.Embed(
            title="Pari annulé",
            description="Tu n'as plus assez de lucioles pour cette mise.",
            color=discord.Color.red(),
        )
    outcome, payout = result
    won = payout > 0
    if won:
        text = f"Yggdrasil a tiré {_label(outcome)}. Tu gagnes **+{format_number(payout - bet)}** lucioles !"
    else:
        text = f"Yggdrasil a tiré {_label(outcome)}. Tu perds **{format_number(bet)}** lucioles."
    embed = discord.Embed(
        title="Pari gagné !" if won else "Pari perdu",
        description=text,
        color=discord.Color.brand_green() if won else discord.Color.red(),
    )
    embed.add_field(name="Lucioles", value=format_number(player["fireflies"]))
    embed.add_field(name="Gagné au gambling (total)", value=format_number(player["gambling_won"]))
    embed.add_field(name="Perdu au gambling (total)", value=format_number(player["gambling_lost"]))
    return embed


class GamblingView(discord.ui.View):
    def __init__(self, owner_id: int, name: str, color: str, bet: int):
        super().__init__(timeout=TIMEOUT)
        self.owner_id = owner_id
        self.name = name
        self.color = color
        self.bet = bet
        self.done = False
        self.interaction: discord.Interaction | None = None

    async def start(self, interaction: discord.Interaction):
        self.interaction = interaction
        await interaction.response.send_message(
            embed=confirm_embed(self.color, self.bet), view=self, ephemeral=True
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Ce pari appartient à un autre joueur.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.done:  # double clic : un seul tirage par pari
            await interaction.response.defer()
            return
        self.done = True
        self.stop()
        player, result = await db.gamble(self.owner_id, self.name, self.color, self.bet)
        await interaction.response.edit_message(
            embed=result_embed(self.color, self.bet, player, result), view=None
        )

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.done = True
        self.stop()
        await interaction.response.edit_message(
            embed=discord.Embed(title="Pari annulé", description="Aucune luciole n'a été misée.", color=discord.Color.light_grey()),
            view=None,
        )

    async def on_timeout(self):
        if self.done or self.interaction is None:
            return
        self.done = True
        await self.interaction.edit_original_response(
            embed=discord.Embed(title="Pari expiré", description="Aucune luciole n'a été misée.", color=discord.Color.light_grey()),
            view=None,
        )
