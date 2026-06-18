import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio

TOKEN = os.environ.get("TOKEN")
SALON_RESERVATIONS_ID = int(os.environ.get("SALON_RESERVATIONS_ID"))
ROLE_ADMIN_ID = int(os.environ.get("ROLE_ADMIN_ID"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def send_ephemeral_temp(interaction, message, delay=3):
    await interaction.response.send_message(message, ephemeral=True)
    await asyncio.sleep(delay)
    try:
        await interaction.delete_original_response()
    except Exception:
        pass

# ──────────────────────────────────────────────
# MODAL : formulaire de réservation
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
                "❌ Salon de réservations introuvable.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📋 Nouvelle demande de réservation",
            color=discord.Color.orange()
        )
        embed.add_field(name="👤 Demandeur", value=interaction.user.mention, inline=False)
        embed.add_field(name="📅 Date", value=self.date.value, inline=False)
        embed.add_field(name="🕐 Sessions", value=self.sessions.value, inline=False)
        embed.add_field(name="👥 Nombre de joueurs", value=self.joueurs.value, inline=False)
        embed.set_footer(text="⏳ — EN ATTENTE DE VALIDATION PAR UN ADMIN —")

        view = ValidationView(
            demandeur=interaction.user,
            date=self.date.value,
            sessions=self.sessions.value,
            joueurs=self.joueurs.value
        )
        await salon.send(embed=embed, view=view)
        await send_ephemeral_temp(interaction, "✅ Ta réservation a bien été envoyée ! En attente de validation.", delay=5)


# ──────────────────────────────────────────────
# MODAL : raison du refus
# ──────────────────────────────────────────────
class RefusModal(discord.ui.Modal, title="❌ Raison du refus"):

    raison = discord.ui.TextInput(
        label="Raison du refus",
        placeholder="ex: Créneau déjà pris",
        required=True,
        max_length=200,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, demandeur, date, sessions, joueurs, message_embed, view):
        super().__init__()
        self.demandeur = demandeur
        self.date = date
        self.sessions = sessions
        self.joueurs = joueurs
        self.message_embed = message_embed
        self.validation_view = view

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.message_embed.embeds[0]
        embed.color = discord.Color.red()
        embed.set_footer(text=f"❌ — REFUSÉE PAR {interaction.user.display_name.upper()} —")
        embed.add_field(name="❌ Raison du refus", value=self.raison.value, inline=False)

        # Remplace les boutons par uniquement "Nouvelle réservation"
        new_view = SeulementNouvelleReservationView()
        await self.message_embed.edit(embed=embed, view=new_view)
        await send_ephemeral_temp(interaction, "❌ Réservation refusée.", delay=3)

        try:
            await self.demandeur.send(
                f"❌ **Votre réservation de session a été refusée par {interaction.user.display_name}**\n\n"
                f"📅 Réservation du **{self.date}** aux sessions de **{self.sessions}** pour **{self.joueurs}** joueur(s)\n\n"
                f"**Raison du refus :** {self.raison.value}\n\n"
                f"─────────────────────\n"
                f"*⚠️ Ce message est envoyé automatiquement, merci de ne pas y répondre, personne ne le recevra.*"
            )
        except Exception:
            pass


# ──────────────────────────────────────────────
# VUE : uniquement le bouton Nouvelle réservation
# ──────────────────────────────────────────────
class SeulementNouvelleReservationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Nouvelle réservation", style=discord.ButtonStyle.primary, row=0)
    async def nouvelle_reservation(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReservationModal())


# ──────────────────────────────────────────────
# BOUTONS : Accepter / Refuser / Nouvelle réservation
# ──────────────────────────────────────────────
class ValidationView(discord.ui.View):
    def __init__(self, demandeur, date, sessions, joueurs):
        super().__init__(timeout=None)
        self.demandeur = demandeur
        self.date = date
        self.sessions = sessions
        self.joueurs = joueurs

    def est_admin(self, interaction: discord.Interaction) -> bool:
        role = interaction.guild.get_role(ROLE_ADMIN_ID)
        return role in interaction.user.roles

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.success, row=0)
    async def accepter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.est_admin(interaction):
            await send_ephemeral_temp(interaction, "❌ Tu n'as pas la permission.", delay=3)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text=f"✅ — ACCEPTÉE PAR {interaction.user.display_name.upper()} —")

        # Remplace les boutons par uniquement "Nouvelle réservation"
        new_view = SeulementNouvelleReservationView()
        await interaction.message.edit(embed=embed, view=new_view)
        await send_ephemeral_temp(interaction, f"✅ Réservation acceptée ! {self.demandeur.mention} a été notifié.", delay=3)

        try:
            await self.demandeur.send(
                f"✅ **Votre réservation de session a été acceptée par {interaction.user.display_name}**\n\n"
                f"📅 Réservation du **{self.date}** aux sessions de **{self.sessions}** pour **{self.joueurs}** joueur(s)\n\n"
                f"─────────────────────\n"
                f"*⚠️ Ce message est envoyé automatiquement, merci de ne pas y répondre, personne ne le recevra.*"
            )
        except Exception:
            pass

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger, row=0)
    async def refuser(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.est_admin(interaction):
            await send_ephemeral_temp(interaction, "❌ Tu n'as pas la permission.", delay=3)
            return

        modal = RefusModal(
            demandeur=self.demandeur,
            date=self.date,
            sessions=self.sessions,
            joueurs=self.joueurs,
            message_embed=interaction.message,
            view=self
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📝 Nouvelle réservation", style=discord.ButtonStyle.primary, row=0)
    async def nouvelle_reservation(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReservationModal())


# ──────────────────────────────────────────────
# BOUTON PERMANENT
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
# COMMANDE /setupresa
# ──────────────────────────────────────────────
@bot.tree.command(name="setupresa", description="Poste le bouton de réservation (admin seulement)")
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
