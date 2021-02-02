import pytest

from smashtheque.helpers.misc import *

@pytest.mark.parametrize("test_input,expected", [
  ("123", False),
  ("9846751827591168", False),
  ("98467518275911680", True),
  ("100525437511290880", True),
  ("608210202952466464", True),
  ("6082102029524664640", False)
])
def test_is_discord_id(test_input, expected):
  assert is_discord_id(test_input) == expected

@pytest.mark.parametrize("test_input,expected", [
  ("nope", False),
  ("<toto:123>", False),
  ("<:toto123>", False),
  ("<:toto:toto>", False),
  ("<:toto:123>", True),
  ("<a:toto:123>", True)
])
def test_is_emoji(test_input, expected):
  assert is_emoji(test_input) == expected

@pytest.mark.parametrize("test_input,expected", [
  (None, None),
  ("", ""),
  ("hello world", "helloworld"),
  ("àâäÀÂÄéèêëÉÈÊËìîïÌÎÏòôöÒÔÖùûüÙÛÜÿŸ", "aaaaaaeeeeeeeeiiiiiioooooouuuuuuyy"),
  ("<>$€,!:", "")
])
def test_normalize_str(test_input, expected):
  assert normalize_str(test_input) == expected

@pytest.mark.parametrize("test_input,expected", [
  (None, ""),
  ("", ""),
  ("123", "<:placeholder:123>")
])
def test_format_emoji(test_input, expected):
  assert format_emoji(test_input) == expected

@pytest.mark.parametrize("test_input,expected", [
  (None, ""),
  ({"emoji": None}, ""),
  ({"emoji": ""}, ""),
  ({"emoji": "123"}, "<:placeholder:123>")
])
def test_format_character(test_input, expected):
  assert format_character(test_input) == expected

@pytest.mark.parametrize("test_input,expected", [
  (None, ""),
  ("", ""),
  ("123", "<@123>")
])
def test_format_discord_user(test_input, expected):
  assert format_discord_user(test_input) == expected

@pytest.mark.parametrize("test_input,expected", [
  (None, ""),
  ({"name": "Hello World", "short_name": ""}, "Hello World ()"),
  ({"name": "", "short_name": "HW"}, " (HW)"),
  ({"name": "Hello World", "short_name": "HW"}, "Hello World (HW)")
])
def test_format_team(test_input, expected):
  assert format_team(test_input) == expected

@pytest.mark.parametrize("test_input,expected", [
  (None, ""),
  ({"name": "paris"}, "Paris"),
  ({"name": "PARIS"}, "Paris")
])
def test_format_location(test_input, expected):
  assert format_location(test_input) == expected
