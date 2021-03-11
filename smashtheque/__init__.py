import django
django.setup()

from .smashtheque import Smashtheque

async def setup(bot):
    n = Smashtheque(bot)
    await n.initialize()
    bot.add_cog(n)
