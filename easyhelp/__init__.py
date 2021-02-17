from .easyhelp import EasyHelp

async def setup(bot):
    n = EasyHelp(bot)
    bot.add_cog(n)