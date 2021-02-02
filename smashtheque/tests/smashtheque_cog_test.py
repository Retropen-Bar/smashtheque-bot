import pytest

from redbot.core.bot import Red

from smashtheque.smashtheque_cog import SmashthequeCog

def test_smashtheque_cog_init():
  o = SmashthequeCog(None)
  assert isinstance(o, SmashthequeCog)
