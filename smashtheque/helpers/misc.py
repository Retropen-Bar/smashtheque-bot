from collections import UserDict
from collections.abc import Mapping
import re
import unicodedata

def is_discord_id(v):
  return v.isdigit() and (len(str(v)) == 17 or len(str(v)) == 18)

def is_emoji(v):
  return re.search(r"<a?:(\w+):(\d+)>", v) != None

def match_url(v):
  return re.match(r"^((http[s]?|ftp):\/)?\/?([^:\/\s]+)((\/\w+)*\/)([\w\-\.]+[^#?\s]+)(.*)?(#[\w\-]+)?$", v)

def normalize_str(s):
  s1 = ''.join(
    c for c in unicodedata.normalize('NFD', s)
    if unicodedata.category(c) != 'Mn'
  )
  s2 = re.sub("[^a-zA-Z]+", "", s1)
  return s2.lower()

class Map(UserDict):
  def __getattr__(self, attr):
    val = self.data[attr]
    if isinstance(val, Mapping):
        return Map(val)
    return val

def format_emoji(emoji_id):
  return f"<:placeholder:{emoji_id}>"

def format_character(character):
  return format_emoji(character["emoji"])

def format_discord_user(discord_id):
  return f"<@{discord_id}>"

def format_team(team):
  return "{0} ({1})".format(team["name"], team["short_name"])

def format_location(location):
  return location["name"].title()
