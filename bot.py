import discord
from discord import client
import discord
from discord.ext import commands


import os

from smashtheque.smashtheque import Smashtheque
from error_handler import CommandErrorHandler

# make a minimalist bot with cogs
client = commands.Bot(command_prefix='&')

# get BOT_TOKEN from environ

BOT_TOKEN = os.environ.get('BOT_TOKEN')

client.add_cog(Smashtheque(client))
client.add_cog(CommandErrorHandler(client))
client.run("NzQ1MDIyNjE4MzU2NDE2NTcy.XzruYg.Pq2cYiJfARz-1A_ay3J1YVNe8kg")