import discord
from discord import client
import discord
from discord.ext import commands

from discord import Intents


import os

from smashtheque.smashtheque import Smashtheque
from error_handler import CommandErrorHandler

intents = Intents.none()

intents.messages = True

# make a minimalist bot with cogs
client = commands.Bot(command_prefix='&', intents=intents)

# get BOT_TOKEN from environ

BOT_TOKEN = os.environ.get('BOT_TOKEN')

client.add_cog(Smashtheque(client))
client.add_cog(CommandErrorHandler(client))
client.run(BOT_TOKEN)