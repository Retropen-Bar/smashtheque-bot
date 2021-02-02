import pytest

from smashtheque.helpers.misc import *

@pytest.mark.parametrize("test_input,expected", [("608210202952466464", True), ("123", False)])
def test_is_discord_id(test_input, expected):
    assert is_discord_id(test_input) == expected
