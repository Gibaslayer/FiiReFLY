import discord

import config
import database as db
import game

EMBED_COLOR = discord.Color.gold()

PAGES = (("accueil", "Accueil"), ("atelier", "Atelier"), ("boutique", "Boutique"), ("arbre", "Arbre"))


def format_number(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def _counts(player: dict) -> tuple[int, int, int, int]:
    return tuple(player[column] for column in db.COLLECTOR_COLUMNS)


def build_embed(page: str, player: dict, notice: str = "") -> discord.Embed:
    treelevel = player["treelevel"]
    mult = game.multiplier(treelevel)
    fireflies = format_number(player["fireflies"])

    if page == "accueil":
        embed = discord.Embed(
            title="FiiReFLY Fabric",
            description="Bienvenue dans votre atelier de lucioles !\nUtilisez les boutons ci-dessous pour naviguer.",
            color=EMBED_COLOR,
        )
        production = game.production_per_second(_counts(player), treelevel)
        embed.add_field(name="Lucioles", value=fireflies)
        embed.add_field(name="Production", value=f"{format_number(production)} / s")
        embed.add_field(name="Arbre", value=f"Niveau {treelevel} (x{mult})")

    elif page == "atelier":
        embed = discord.Embed(
            title="Atelier",
            description=f"Capturez des lucioles à la main : **+{format_number(game.click_gain(treelevel))}** par capture.",
            color=EMBED_COLOR,
        )
        embed.add_field(name="Lucioles", value=fireflies)

    elif page == "boutique":
        embed = discord.Embed(
            title="Boutique",
            description=f"Achetez des collecteurs pour récolter automatiquement.\nLucioles : **{fireflies}**",
            color=EMBED_COLOR,
        )
        for i, owned in enumerate(_counts(player)):
            rate = config.COLLECTOR_RATES[i] * mult
            cost = format_number(game.collector_cost(i, owned))
            embed.add_field(
                name=f"{config.COLLECTOR_NAMES_SINGULAR[i]} · {format_number(rate)}/s",
                value=f"Prix : {cost} · Possédés : {format_number(owned)}",
                inline=False,
            )

    elif page == "arbre":
        embed = discord.Embed(
            title="Arbre de vie",
            description=(
                "Renaître sacrifie vos lucioles et vos collecteurs "
                "pour faire grandir l'arbre, ce qui multiplie définitivement vos gains."
            ),
            color=EMBED_COLOR,
        )
        embed.add_field(name="Niveau actuel", value=f"{treelevel} (x{mult})")
        embed.add_field(name="Prochain niveau", value=f"{treelevel + 1} (x{mult + 1})")
        embed.add_field(name="Coût", value=f"{format_number(game.rebirth_cost(treelevel))} lucioles")

    else:  # confirmation
        embed = discord.Embed(
            title="Renaître ?",
            description=(
                "Vous allez perdre **toutes vos lucioles et tous vos collecteurs**.\n"
                f"Votre arbre passera au niveau **{treelevel + 1}** (x{mult + 1})."
            ),
            color=EMBED_COLOR,
        )

    if notice:
        embed.set_footer(text=notice)
    return embed


class View_fabric(discord.ui.View):
    def __init__(self, owner_id: int, name: str, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.name = name
        self.page = "accueil"
        self.player: dict = {}
        self.notice = ""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Cette fenêtre appartient à un autre joueur. Lancez /fenetre pour ouvrir la vôtre.",
                ephemeral=True,
            )
            return False
        return True

    async def start(self, interaction: discord.Interaction):
        self.player = await db.get_player(self.owner_id, self.name)
        self._build_items()
        await interaction.response.send_message(
            embed=build_embed(self.page, self.player), view=self, ephemeral=True
        )

    def _add(self, label: str, style: discord.ButtonStyle, callback, row: int, disabled: bool = False):
        button = discord.ui.Button(label=label, style=style, row=row, disabled=disabled)
        button.callback = callback
        self.add_item(button)

    def _build_items(self):
        self.clear_items()
        for page, label in PAGES:
            style = discord.ButtonStyle.primary if page == self.page else discord.ButtonStyle.secondary
            self._add(label, style, self._go(page), row=0)

        fireflies = self.player["fireflies"]
        if self.page == "atelier":
            self._add("Capturer", discord.ButtonStyle.success, self._click, row=1)
        elif self.page == "boutique":
            for i, owned in enumerate(_counts(self.player)):
                affordable = fireflies >= game.collector_cost(i, owned)
                self._add(f"Acheter : {config.COLLECTOR_NAMES_SINGULAR[i]}", discord.ButtonStyle.secondary,
                          self._buy(i), row=1 + i // 2, disabled=not affordable)
        elif self.page == "arbre":
            affordable = fireflies >= game.rebirth_cost(self.player["treelevel"])
            self._add("Renaître", discord.ButtonStyle.danger, self._go("confirmation"), row=1, disabled=not affordable)
        elif self.page == "confirmation":
            self._add("Confirmer", discord.ButtonStyle.danger, self._rebirth, row=1)
            self._add("Annuler", discord.ButtonStyle.secondary, self._go("arbre"), row=1)

    async def _show(self, interaction: discord.Interaction, page: str | None = None, notice: str = ""):
        if page:
            self.page = page
        self.notice = notice
        self._build_items()
        await interaction.response.edit_message(
            embed=build_embed(self.page, self.player, self.notice), view=self
        )

    def _go(self, page: str):
        async def callback(interaction: discord.Interaction):
            self.player = await db.get_player(self.owner_id, self.name)
            await self._show(interaction, page)
        return callback

    async def _click(self, interaction: discord.Interaction):
        self.player, ok = await db.click(self.owner_id, self.name)
        await self._show(interaction, notice="" if ok else "Trop rapide : patientez une seconde.")

    def _buy(self, index: int):
        async def callback(interaction: discord.Interaction):
            self.player, ok = await db.buy_collector(self.owner_id, self.name, index)
            await self._show(interaction, notice="" if ok else "Pas assez de lucioles.")
        return callback

    async def _rebirth(self, interaction: discord.Interaction):
        self.player, ok = await db.rebirth(self.owner_id, self.name)
        if ok:
            await self._show(interaction, "arbre", "Votre arbre a grandi !")
        else:
            await self._show(interaction, "arbre", "Pas assez de lucioles pour renaître.")
