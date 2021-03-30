import discord

from discord.ext import commands as dpy_commands

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands.help import HelpTarget


class HelpFormatter(commands.RedHelpFormatter):
    async def send_help(
        self, ctx: commands.Context, help_for: HelpTarget, *, from_help_command: bool
    ):
        if help_for is not None or isinstance(help_for, dpy_commands.bot.BotBase):
            if help_for == "all":
                help_for = None
            return await super().send_help(ctx, help_for, from_help_command=from_help_command)
        p = ctx.clean_prefix
        embed = discord.Embed.from_dict(
            {
      "title": "Aide de la Smashthèque",
      "description": "Vérifiez toujours au préalable que vous n'êtes pas déjà dans la base de données",
      "color": 16265778,
      "fields": [
        {
          "name": "Liste des commandes :",
          "value": f"Sachant qu'il faut toujours rajouter quelque chose derrière le nom de commande (par exemple un emote de perso ou un nom de team) \n"
          f"`{ctx.clean_prefix}ajouterpersos` pour ajouter un ou des persos\n"
          f"`{ctx.clean_prefix}enleverpersos` pour enlever des persos\n"
          f"`{ctx.clean_prefix}remplacerpersos` pour remplacer tout vos persos\n"
          f"`{ctx.clean_prefix}persos` pour avoir la liste des persos que le bot reconnait\n"
          f"`{ctx.clean_prefix}integrer` pour s'ajouter à une team existante (utiliser le nom court)\n"
          f"`{ctx.clean_prefix}quitter` pour quitter une team (nom court aussi)\n"
          f"`{ctx.clean_prefix}changerpseudo` pour changer votre pseudo\n"
          f"`{ctx.clean_prefix}chercherjoueur` pour chercher un joueur par son pseudo\n"
          f"`{ctx.clean_prefix}bracket` pour ajouter une édition à un tournoi dont vous êtes l'admin\n"
          f"`{ctx.clean_prefix}annoncescircuit` pour suivre les annonces du 2v2 smashtheque series"
        },
        {
          "name": "Pour créer un joueur :",
          "value": f"Pour créer un joueur, utilisez la commande `{ctx.clean_prefix}creerjoueur`. Pour plus d'infos sur la création d'un joueur, utilisez la commande `{ctx.clean_prefix}help creerjoueur`"
        },
        {
          "name": "Liens importants :",
          "value": "**[Accueil](https://smashtheque.fr) • [Serveur Discord](https://discord.gg/2HwUAyw) • [Lien Du Bot](https://smashtheque.fr/bot)**"
        }
      ],
      "author": {
        "name": "\u200b",
        "icon_url": "https://s3.eu-west-3.amazonaws.com/static.smashtheque.fr/img/smashtheque-256.png"
      },
          "footer": {
        "text": "Avec ❤️ par les admins Smashthèque"
      }
    }
        )

        help_settings = await commands.HelpSettings.from_context(ctx)
        await self.send_pages(ctx, pages=[embed], embed=True, help_settings=help_settings)


class EasyHelp(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.bot.set_help_formatter(HelpFormatter())

    def cog_unload(self):
        self.bot.reset_help_formatter()
