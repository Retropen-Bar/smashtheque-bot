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
bot = commands.Bot(command_prefix='&', intents=intents)

# get BOT_TOKEN from environ

BOT_TOKEN = os.environ.get('BOT_TOKEN')


bot.add_cog(Smashtheque(bot))
bot.add_cog(CommandErrorHandler(bot))
guild = discord.Object(id=737431333478989907)  # you can use a full discord.Guild as the method accepts a Snowflake

bot.tree.copy_global_to(guild=guild)

bot.run(BOT_TOKEN)