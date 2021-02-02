import pytest

from smashtheque.smashtheque import Smashtheque

def test_smashtheque_init():
  o = Smashtheque()
  assert isinstance(o, Smashtheque)
