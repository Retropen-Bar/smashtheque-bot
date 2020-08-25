from .smashtheque import Smashtheque


def setup(bot):
    n = Smashtheque(bot)
    bot.add_cog(n)