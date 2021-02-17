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
        embed = discord.Embed(title="Help Smashthèque", description="Not working")

        help_settings = await commands.HelpSettings.from_context(ctx)
        await self.send_pages(ctx, pages=[embed], embed=True, help_settings=help_settings)


class EasyHelp(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.bot.set_help_formatter(HelpFormatter())

    def cog_unload(self):
        self.bot.reset_help_formatter()
