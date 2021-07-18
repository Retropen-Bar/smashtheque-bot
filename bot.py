import discord
from discord import client
import discord
from discord.ext import commands

from redbot.core import commands as redCommands

from babel import Locale as BabelLocale, UnknownLocaleError
from redbot.core.i18n import set_contextual_locale

import os

from smashtheque.smashtheque import Smashtheque

# make a minimalist bot with cogs
client = commands.Bot(command_prefix='&')

# get BOT_TOKEN from environ

BOT_TOKEN = os.environ.get('BOT_TOKEN')

client.add_cog(Smashtheque(client))
client.run(BOT_TOKEN)
