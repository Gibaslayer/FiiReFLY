import discord

import config
import database as db
import game

EMBED_COLOR = discord.Color.gold()

PAGES = (("accueil", "🏠 Accueil"), ("atelier", "🛠️ Atelier"), ("boutique", "🏪 Boutique"), ("arbre", "🌲Arbre"))


def format_number(n: int) -> str:
    return f"{n:,}".replace(",", " ")


COMPACT_UNITS = ("", "K", "M", "Md", "Bn", "Bd", "Tn")  # milliers, millions, milliards, billions, billiards, trillions


def format_compact(n: int) -> str:
    """Version courte : 950 -> 950, 1 500 -> 1,5K, 2 000 000 -> 2M, 3 000 000 000 -> 3Md."""
    unit = 0
    while n >= 1000 ** (unit + 1) and unit < len(COMPACT_UNITS) - 1:
        unit += 1
    if unit == 0:
        return str(n)
    whole, decimal = divmod(n * 10 // 1000 ** unit, 10)  # une décimale, tronquée
    return f"{whole},{decimal}{COMPACT_UNITS[unit]}" if decimal else f"{whole}{COMPACT_UNITS[unit]}"


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
        gain = game.click_gain(treelevel, _counts(player), player["click_upgrades"])
        embed = discord.Embed(
            title="Atelier",
            description=f"Capturez des lucioles à la main : **+{format_number(gain)}** par capture.",
            color=EMBED_COLOR,
        )
        embed.add_field(name="Lucioles", value=fireflies)
        embed.add_field(name="Amélioration de clic", value=f"Niveau {format_number(player['click_upgrades'])}")

    elif page == "boutique":
        embed = discord.Embed(
            title="Boutique",
            description=(
                "Achetez des collecteurs pour récolter automatiquement.\n"
                f"Tous les {config.MILESTONE_STEP} exemplaires d'un même collecteur, sa production double.\n"
                f"Lucioles : **{fireflies}**"
            ),
            color=EMBED_COLOR,
        )
        for i, owned in enumerate(_counts(player)):
            rate = game.collector_rate(i, owned, treelevel)
            cost = format_number(game.collector_cost(i, owned))
            next_milestone = (owned // config.MILESTONE_STEP + 1) * config.MILESTONE_STEP
            embed.add_field(
                name=f"{config.COLLECTOR_NAMES_SINGULAR[i]} · {format_number(rate)}/s chacun",
                value=(f"Prix : {cost} · Possédés : {format_number(owned)} "
                       f"(x{format_number(game.milestone_bonus(owned))}) · Prochain palier : {next_milestone}"),
                inline=False,
            )
        upgrades = player["click_upgrades"]
        embed.add_field(
            name=f"Amélioration de clic · niveau {format_number(upgrades)}",
            value=(f"Prix : {format_number(game.click_upgrade_cost(upgrades))} · "
                   f"Chaque niveau ajoute {100 // config.CLICK_UPGRADE_RATIO} % de la production par seconde à chaque capture"),
            inline=False,
        )

    elif page == "arbre":
        embed = discord.Embed(
            title="Arbre de vie",
            description=(
                "Renaître sacrifie vos lucioles, vos collecteurs et vos améliorations "
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
                "Vous allez perdre **toutes vos lucioles, tous vos collecteurs et vos améliorations**.\n"
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
            style = discord.ButtonStyle.primary if page == self.page else discord.ButtonStyle.green
            self._add(label, style, self._go(page), row=0)

        fireflies = self.player["fireflies"]
        if self.page == "atelier":
            self._add("Capturer", discord.ButtonStyle.gray, self._click, row=1)
        elif self.page == "boutique":
            for i, owned in enumerate(_counts(self.player)):
                affordable = fireflies >= game.collector_cost(i, owned)
                self._add(f"Acheter : {config.COLLECTOR_NAMES_SINGULAR[i]}", discord.ButtonStyle.secondary,
                          self._buy(i), row=1 + i // 2, disabled=not affordable)
            upgrade_affordable = fireflies >= game.click_upgrade_cost(self.player["click_upgrades"])
            self._add("Acheter : Amélioration de clic", discord.ButtonStyle.secondary,
                      self._buy_upgrade, row=3, disabled=not upgrade_affordable)
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

    async def _buy_upgrade(self, interaction: discord.Interaction):
        self.player, ok = await db.buy_click_upgrade(self.owner_id, self.name)
        await self._show(interaction, notice="" if ok else "Pas assez de lucioles.")

    async def _rebirth(self, interaction: discord.Interaction):
        self.player, ok = await db.rebirth(self.owner_id, self.name)
        if ok:
            await self._show(interaction, "arbre", "Votre arbre a grandi !")
        else:
            await self._show(interaction, "arbre", "Pas assez de lucioles pour renaître.")
