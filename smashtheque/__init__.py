from .smashtheque_cog import SmashthequeCog

async def setup(bot):
  n = SmashthequeCog(bot)
  await n.initialize()
  bot.add_cog(n)
