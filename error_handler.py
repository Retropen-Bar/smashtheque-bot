import discord
import traceback
import sys
from discord.ext import commands

# This file is important, it contains the error handler for the bot.
# The error handler doesn't just catch errors, it also sends help when a command isn't complete 

class CommandErrorHandler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def get_command_signature(ctx: commands.Context, command: commands.Command) -> str:
        parent = command.parent
        entries = []
        while parent is not None:
            if not parent.signature or parent.invoke_without_command:
                entries.append(parent.name)
            else:
                entries.append(parent.name + " " + parent.signature)
            parent = parent.parent
        parent_sig = (" ".join(reversed(entries)) + " ") if entries else ""

        return f"{ctx.clean_prefix}{parent_sig}{command.name} {command.signature}"

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        """The event triggered when an error is raised while invoking a command.
        Parameters
        ------------
        ctx: commands.Context
            The context used for command invocation.
        error: commands.CommandError
            The Exception raised.
        """

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return

        # This prevents any cogs with an overwritten cog_command_error being handled here.
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (commands.CommandNotFound, )

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored):
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f'{ctx.command} has been disabled.')

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
            except discord.HTTPException:
                pass

        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(description=f"```Syntaxe : {self.get_command_signature(ctx, ctx.command)}```\n{ctx.command.help}", color=0xFF0000)
            embed.set_author(name="Aide Smashthèque", icon_url=ctx.me.avatar)
            embed.set_footer(text="Avec ❤️ par les admins Smashthèque - s!help pour plus d'informations")
            await ctx.send(embed=embed)

        else:
            # All other Errors not returned come here. And we can just print the default TraceBack.
            print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            