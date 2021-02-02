import re
import unicodedata

def is_discord_id(v):
  return v.isdigit() and (len(str(v)) == 17 or len(str(v)) == 18)

def is_emoji(v):
  return re.search(r"<a?:(\w+):(\d+)>", v) != None

def normalize_str(s):
  if not s:
    return s
  s1 = ''.join(
    c for c in unicodedata.normalize('NFD', s)
    if unicodedata.category(c) != 'Mn'
  )
  s2 = re.sub("[^a-zA-Z]+", "", s1)
  return s2.lower()

def format_emoji(emoji_id):
  if not emoji_id:
    return ""
  return f"<:placeholder:{emoji_id}>"

def format_character(character):
  if not character:
    return ""
  return format_emoji(character["emoji"])

def format_discord_user(discord_id):
  if not discord_id:
    return ""
  return f"<@{discord_id}>"

def format_team(team):
  if not team:
    return ""
  return "{0} ({1})".format(team["name"], team["short_name"])

def format_location(location):
  if not location:
    return ""
  return location["name"].title()
