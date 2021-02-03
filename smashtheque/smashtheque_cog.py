from redbot.core import commands

import discord
from redbot.core.bot import Red
from typing import Optional
import rollbar
import os

from .smashtheque import Smashtheque
from .helpers.api import ApiClient

class SmashthequeCog(Smashtheque, commands.Cog):
    async def initialize(self):
        if 'ROLLBAR_TOKEN' in os.environ and os.environ['ROLLBAR_TOKEN']:
            rollbar_token = os.environ['ROLLBAR_TOKEN']
            if 'ROLLBAR_ENV' in os.environ and os.environ['ROLLBAR_ENV']:
                rollbar_env = os.environ['ROLLBAR_ENV']
            else:
                rollbar_env = 'production'

        else:
            rollbar_token = await self.bot.get_shared_api_tokens("smashtheque")
            rollbar_token = rollbar_token["token"]
            if 'environment' in rollbar_token:
                rollbar_env = rollbar_token["environment"]
            else:
                rollbar_env = 'production'
        rollbar.init(rollbar_token, rollbar_env)

        try:
            if 'SMASHTHEQUE_API_URL' in os.environ and os.environ['SMASHTHEQUE_API_URL']:
                api_base_url = os.environ['SMASHTHEQUE_API_URL']
            else:
                _api_base_url = await self.bot.get_shared_api_tokens("smashtheque")
                api_base_url = _api_base_url["url"]
            print(f"Smashthèque API base URL set to {api_base_url}")
            if 'SMASHTHEQUE_API_TOKEN' in os.environ and os.environ['SMASHTHEQUE_API_TOKEN']:
                bearer = os.environ['SMASHTHEQUE_API_TOKEN']
            else:
                bearer = await self.bot.get_shared_api_tokens("smashtheque")
                bearer = bearer["bearer"]

            self.api = ApiClient(apiBaseUrl=api_base_url, bearerToken=bearer)
        except:
            rollbar.report_exc_info()
            raise

    def __init__(self, bot: Red):
        self.bot = bot

    def cog_unload(self):
        self.api.unload()

    # -------------------------------------------------------------------------
    # COMMANDS
    # -------------------------------------------------------------------------

    @commands.command(usage="<nom>")
    async def creerville(self, ctx, *, name):
        """cette commande va vous permettre d'ajouter une ville dans la Smashthèque.
        \n\nVous devez préciser son nom.
        \n\n\nExemples : \n- creerville Paris\n- creerville Lyon\n"""

        try:
            await self.do_createlocation(ctx, name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<nom>")
    async def creerpays(self, ctx, *, name):
        """cette commande va vous permettre d'ajouter un pays dans la Smashthèque.
        \n\nVous devez préciser son nom.
        \n\n\nExemples : \n- creerpays Belgique\n"""

        try:
            await self.do_createlocation(ctx, name, country=True)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<pseudo> <emojis ou noms de persos> [team] [localisation] [ID Discord]")
    async def creerjoueur(self, ctx, *, arg):
        """cette commande va vous permettre d'ajouter un joueur dans la Smashthèque.
        \n\nVous devez ajouter au minimum le pseudo et les personnages joués (dans l'ordre).
        \n\nVous pouvez aussi ajouter sa team, sa localisation et, s'il possède un compte Discord, son ID pour qu'il puisse modifier lui-même son compte.
        \n\nVous pouvez récupérer l'ID avec les options de developpeur (activez-les dans l'onglet Apparence des paramètres de l'utilisateur, puis faites un clic droit sur l'utilisateur et sélectionnez \"Copier ID\".)
        \n\n\nExemples : \n- creerjoueur Pixel <:Yoshi:737480513744273500> <:Bowser:737480497332224100>\n- creerjoueur Pixel Yoshi Bowser\n- creerjoueur red <:Joker:737480520052637756> LoS Paris 332894758076678144\n"""

        try:
            await self.do_addplayer(ctx, arg)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<pseudo>")
    async def jesuis(self, ctx, *, pseudo):
        """cette commande va vous permettre d'associer votre compte Discord à un joueur de la Smashthèque.
        \n\nVous devez préciser un pseudo.
        \n\n\nExemples : \n- jesuis Pixel\n- jesuis red\n"""

        try:
            await self.do_link(ctx, pseudo, ctx.author.id)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<pseudo> <ID Discord>")
    @commands.admin_or_permissions(administrator=True)
    async def associer(self, ctx, *, arg):
        """cette commande va vous permettre d'associer un compte Discord à un joueur de la Smashthèque.
        \n\nVous devez préciser son pseudo et son ID Discord.
        \n\n\nExemples : \n- associer Pixel 608210202952466464\n- associer red 332894758076678144\n"""

        try:
            args = arg.split()
            pseudo = ' '.join(args[:-1])
            discord_id = args[-1]
            await self.do_link(ctx, pseudo, discord_id)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def jenesuispas(self, ctx):
        """cette commande permet de dissocier votre compte Discord d'un joueur de la Smashthèque.
        \n\n\nExemples : \n- jenesuispas\n"""

        try:
            await self.do_unlink(ctx, ctx.author)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<ID Discord>")
    @commands.admin_or_permissions(administrator=True)
    async def dissocier(self, ctx, *, target_member: discord.Member):
        """cette commande permet de dissocier un compte Discord d'un joueur de la Smashthèque.
        \n\nVous devez préciser son ID Discord.
        \n\n\nExemples : \n- dissocier 608210202952466464\n- dissocier 332894758076678144\n"""

        try:
            await self.do_unlink(ctx, target_member)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<ID Discord>")
    @commands.admin_or_permissions(administrator=True)
    async def quiest(self, ctx, *, target_member: discord.Member):
        try:
            await self.do_showplayer(ctx, target_member)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    async def quisuisje(self, ctx):
        try:
            await self.do_showplayer(ctx, ctx.author)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<nouveau pseudo>")
    async def changerpseudo(self, ctx, *, name):
        try:
            await self.do_editname(ctx, ctx.author.id, name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    async def persos(self, ctx):
        try:
            await self.do_listavailablecharacters(ctx)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<emojis ou noms de persos>")
    async def ajouterpersos(self, ctx, *, emojis):
        try:
            await self.do_addcharacters(ctx, ctx.author.id, emojis)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<emojis ou noms de persos>")
    async def enleverpersos(self, ctx, *, emojis):
        try:
            await self.do_removecharacters(ctx, ctx.author.id, emojis)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<emojis ou noms de persos>")
    async def remplacerpersos(self, ctx, *, emojis):
        try:
            await self.do_replacecharacters(ctx, ctx.author.id, emojis)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<team>")
    async def quitter(self, ctx, *, team_short_name):
        try:
            await self.do_removeteam(ctx, ctx.author.id, team_short_name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<team>")
    async def integrer(self, ctx, *, team_short_name):
        try:
            await self.do_addteam(ctx, ctx.author.id, team_short_name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<localisation>")
    async def enleverlocalisation(self, ctx, *, location_name):
        try:
            await self.do_removelocation(ctx, ctx.author.id, location_name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<localisation>")
    async def ajouterlocalisation(self, ctx, *, location_name):
        try:
            await self.do_addlocation(ctx, ctx.author.id, location_name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<pseudo>")
    async def chercherjoueur(self, ctx, *, name):
        try:
            await self.do_findplayer(ctx, name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    async def pileouface(self, ctx):
        try:
            await self.do_chifoumi(ctx)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    async def majlogo(self, ctx):
        """Utilisez cette commande avec une image pour changer le logo de votre team. \n
        Vous devez être administrateur de la team dont vous voulez changer le logo."""
        try:
            await self.maj_team_infos(ctx, "logo")
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    async def majroster(self, ctx):
        """Utilisez cette commande avec une image pour changer le roster de votre team. \n
        Vous devez être administrateur de la team dont vous voulez changer le roster."""
        try:
            await self.maj_team_infos(ctx, "roster")
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    async def tournoi(self, ctx, bracket: Optional[str]):
        """Cette commande permet aux TOs d'ajouter une édition de leur tournois dans la smashtheque"""
        try:
            await self.do_addedition(ctx, bracket)
        except:
            rollbar.report_exc_info()
            raise
