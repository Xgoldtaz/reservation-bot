import discord
from discord.ext import commands
from discord import app_commands

# ⚙️ CONFIG — modifie ces valeurs
import os
TOKEN = os.environ.get("TOKEN")
SALON_RESERVATIONS_ID = int(os.environ.get("SALON_RESERVATIONS_ID"))
ROLE_ADMIN_ID = int(os.environ.get("ROLE_ADMIN_ID"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ──────────────────────────────────────────────
# MODAL : fenêtre de saisie privée
# ──────────────────────────────────────────────
class ReservationModal(discord.ui.Modal, title="📅 Nouvelle Réservation"):

    date = discord.ui.TextInput(
        label="Date",
        placeholder="ex: Mardi 22 Juin",
        required=True,
        max_length=50
    )

    sessions = discord.ui.TextInput(
        label="Horaires des sessions",
        placeholder="ex: 20h00 et 22h00",
        required=True,
        max_length=100
    )

    joueurs = discord.ui.TextInput(
        label="Nombre de joueurs",
        placeholder="ex: 2",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        salon = interaction.guild.get_channel(SALON_RESERVATIONS_ID)
        if salon is None:
            await interaction.response.send_message(
                "❌ Salon de réservations introuvable. Vérifie l'ID dans le code.",
                ephemeral=True
            )
            return

        # Bloc de réservation propre
        embed = discord.Embed(
            title="📋 Nouvelle demande de réservation",
            color=discord.Color.orange()
        )
        embed.add_field(name="👤 Demandeur", value=interaction.user.mention, inline=False)
        embed.add_field(name="📅 Date", value=self.date.value, inline=True)
        embed.add_field(name="🕐 Sessions", value=self.sessions.value, inline=True)
        embed.add_field(name="👥 Nombre de joueurs", value=self.joueurs.value, inline=True)
        embed.set_footer(text="En attente de validation par un admin")

        view = ValidationView(demandeur=interaction.user)
        await salon.send(embed=embed, view=view)

        await interaction.response.send_message(
            "✅ Ta réservation a bien été envoyée ! En attente de validation.",
            ephemeral=True
        )


# ──────────────────────────────────────────────
# BOUTONS : Accepter / Refuser
# ──────────────────────────────────────────────
class ValidationView(discord.ui.View):
    def __init__(self, demandeur: discord.User):
        super().__init__(timeout=None)
        self.demandeur = demandeur

    def est_admin(self, interaction: discord.Interaction) -> bool:
        role = interaction.guild.get_role(ROLE_ADMIN_ID)
        return role in interaction.user.roles

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.success, row=0)
    async def accepter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.est_admin(interaction):
            await interaction.response.send_message(
                "❌ Tu n'as pas la permission de faire ça.", ephemeral=True
            )
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text=f"✅ Acceptée par {interaction.user.display_name}")

        # Désactiver uniquement les boutons Accepter et Refuser, garder Nouvelle réservation
        self.accepter.disabled = True
        self.refuser.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(
            f"✅ Réservation acceptée ! {self.demandeur.mention} a été notifié.", ephemeral=True
        )

        # Notifier le demandeur en DM
        try:
            await self.demandeur.send(
                f"✅ Ta réservation a été **acceptée** par {interaction.user.display_name} !"
            )
        except Exception:
            pass  # DMs fermés

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger, row=0)
    async def refuser(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.est_admin(interaction):
            await interaction.response.send_message(
                "❌ Tu n'as pas la permission de faire ça.", ephemeral=True
            )
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_footer(text=f"❌ Refusée par {interaction.user.display_name}")

        # Désactiver uniquement les boutons Accepter et Refuser, garder Nouvelle réservation
        self.accepter.disabled = True
        self.refuser.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(
            f"❌ Réservation refusée.", ephemeral=True
        )

        try:
            await self.demandeur.send(
                f"❌ Ta réservation a été **refusée** par {interaction.user.display_name}."
            )
        except Exception:
            pass

    @discord.ui.button(label="📝 Nouvelle réservation", style=discord.ButtonStyle.primary, row=0)
    async def nouvelle_reservation(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReservationModal())


# ──────────────────────────────────────────────
# BOUTON : Nouvelle réservation (message permanent)
# ──────────────────────────────────────────────
class NouvelleReservationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📝 Nouvelle réservation",
        style=discord.ButtonStyle.primary,
        custom_id="nouvelle_reservation"
    )
    async def nouvelle_reservation(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReservationModal())


# ──────────────────────────────────────────────
# COMMANDE SLASH : /setup — poste le bouton permanent
# ──────────────────────────────────────────────
@bot.tree.command(name="setupresa", description="Poste le bouton de réservation dans ce salon (admin seulement)")
async def setupresa(interaction: discord.Interaction):
    role = interaction.guild.get_role(ROLE_ADMIN_ID)
    if role not in interaction.user.roles:
        await interaction.response.send_message("❌ Réservé aux admins.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎮 Système de réservation",
        description="Clique sur le bouton ci-dessous pour faire une nouvelle demande de réservation.",
        color=discord.Color.blurple()
    )
    await interaction.channel.send(embed=embed, view=NouvelleReservationView())
    await interaction.response.send_message("✅ Bouton posté !", ephemeral=True)


# ──────────────────────────────────────────────
# DÉMARRAGE
# ──────────────────────────────────────────────
@bot.event
async def on_ready():
    bot.add_view(NouvelleReservationView())
    synced = await bot.tree.sync()
    print(f"✅ Bot connecté en tant que {bot.user}")
    print(f"✅ {len(synced)} commandes synchronisées")

bot.run(TOKEN)
