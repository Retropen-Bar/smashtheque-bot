import aiohttp
import asyncio
import re

from .misc import *

class ApiClient:

  def __init__(self, apiBaseUrl, bearerToken):
    self.apiBaseUrl = "" if apiBaseUrl is None else apiBaseUrl
    headers = {
      "Authorization": f"Bearer {bearerToken}",
      "Content-Type": "application/json",
    }
    self._session = aiohttp.ClientSession(headers=headers)
    self._characters_cache = {}
    self._characters_names_cache = {}
    self._locations_cache = {}
    self._teams_cache = {}

  def apiUrl(self, collection):
    path = "" if collection is None else collection
    return f"{self.apiBaseUrl}/api/v1/{path}"

  # ---------------------------------------------------------------------------
  # CHARACTERS
  # ---------------------------------------------------------------------------

  async def fetchCharacters(self):
    async with self._session.get(self.apiUrl("characters")) as response:
      # API success
      if response.status == 200:
        characters = await response.json()
        # puts values in cache before responding
        for character in characters:
          self._characters_cache[str(character["id"])] = character
          self._characters_names_cache[normalize_str(character["name"])] = character["id"]
        # respond
        return True, characters

      # API failure
      return False, []

  async def fetchCharactersIfNeeded(self):
    if len(self._characters_cache) < 1 or len(self._characters_names_cache) < 1:
      await self.fetchCharacters()

  async def findCharacterByEmojiTag(self, emoji):
    print(f"findCharacterByEmojiTag({emoji})")
    if not emoji:
      return None
    found = re.search(r"[0-9]+", emoji)
    if found == None:
      return None
    emoji_id = found.group()

    # fill characters cache if empty
    await self.fetchCharactersIfNeeded()

    for character_id in self._characters_cache:
      character = self._characters_cache[str(character_id)]
      if character["emoji"] == emoji_id:
        return character
    return None

  async def findCharacterByName(self, name):
    print(f"findCharacterByName({name})")
    if not name:
      return None
    # fill characters cache if empty
    await self.fetchCharactersIfNeeded()
    # find
    normalizedName = normalize_str(name)
    if normalizedName in self._characters_names_cache:
      character_id = self._characters_names_cache[normalizedName]
      return self._characters_cache.get(str(character_id), None)
    # nothing found
    return None

  async def findCharacterByLabel(self, label):
    if not label:
      return None
    # fill characters cache if empty
    await self.fetchCharactersIfNeeded()
    # option 1: find by emoji
    if is_emoji(label):
      character = await self.findCharacterByEmojiTag(label)
      if character == None:
        return None
      return character
    # option 2: find by name
    character = await self.findCharacterByName(label)
    if character == None:
      return None
    return character
    # nothing found
    return None

  async def isCharacterName(self, v):
    if not v:
      return False
    # fill characters cache if empty
    await self.fetchCharactersIfNeeded()
    # check
    return normalize_str(v) in self._characters_names_cache

  async def isCharacter(self, v):
    found = await self.findCharacterByLabel(v)
    return found != None

  # ---------------------------------------------------------------------------
  # TEAM
  # ---------------------------------------------------------------------------

  async def findTeamByShortName(self, short_name):
    request_url = "{0}?by_short_name_like={1}".format(self.apiUrl("teams"), short_name)
    async with self._session.get(request_url) as response:
      teams = await response.json()
      if teams != []:
        # puts values in cache before responding
        for team in teams:
          self._teams_cache[str(team["id"])] = team
        return teams[0]
      else:
        return None

  async def findTeamById(self, team_id):
    request_url = "{api_url}/{team_id}".format(api_url=self.apiUrl("teams"), team_id=team_id)
    async with self._session.get(request_url) as response:
      team = await response.json()
      return team #or team[0]

  async def updateTeam(self, team_id, data):
    payload = {"team": data}
    request_url = "{0}/{1}".format(self.apiUrl("teams"), team_id)
    async with self._session.patch(request_url, json=payload) as response:
      return response

  # ---------------------------------------------------------------------------
  # TOURNAMENT
  # ---------------------------------------------------------------------------

  async def findTournamentById(self, tournament_id):
    request_url = f"{self.apiUrl('recurring_tournaments')}/{tournament_id}"
    async with self._session.get(request_url) as response:
      tournament = await response.json()
      return tournament

  async def createTournamentEvent(self, data):
    payload = {"tournament_event": data}
    request_url = self.api_url("tournament_events")
    async with self._session.post(request_url, json=payload) as r:
      if r.status == 201:
        return True, 'created'
      if r.status == 200:
        return True, 'updated'
      if r.status == 422:
        result = await r.json()
        err = Map(result)
        return False, err.errors
      return False, {}

  # ---------------------------------------------------------------------------
  # LOCATION
  # ---------------------------------------------------------------------------

  async def findLocationByName(self, name):
    request_url = "{0}?by_name_like={1}".format(self.apiUrl("locations"), name)
    async with self._session.get(request_url) as response:
      locations = await response.json()
      if locations != []:
        # puts values in cache before responding
        for location in locations:
          self._locations_cache[str(location["id"])] = location
        return locations[0]
      else:
        return None

  async def createLocation(self, name, country=False):
    payload = {"name": name}
    if country:
      payload["type"] = "Locations::Country"
    async with self._session.post(self.apiUrl("locations"), json=payload) as r:
      if r.status == 201:
        # location creation went fine
        return True, {}
      if r.status == 422:
        result = await r.json()
        err = Map(result)
        return False, err.errors
      return False, {}

  # ---------------------------------------------------------------------------
  # PLAYER
  # ---------------------------------------------------------------------------

  async def findPlayerById(self, player_id):
    request_url = "{0}/{1}".format(self.apiUrl("players"), player_id)
    async with self._session.get(request_url) as response:
      player = await response.json()
      return player

  async def findPlayerByIds(self, player_ids):
    players = []
    for player_id in player_ids:
      player = await self.findPlayerById(player_id)
      players.append(player)
    return players

  async def findPlayerByDiscordId(self, discord_id):
    request_url = "{0}?by_discord_id={1}".format(self.apiUrl("players"), discord_id)
    async with self._session.get(request_url) as response:
      players = await response.json()
      if len(players) > 0:
        return players[0]
      return None

  async def findPlayersByNameLike(self, name):
    request_url = "{0}?by_name_like={1}".format(self.apiUrl("players"), name)
    async with self._session.get(request_url) as response:
      players = await response.json()
      return players

  async def createPlayer(self, player):
    payload = {"player": player}
    async with self._session.post(self.apiUrl("players"), json=payload) as r:
      if r.status == 201:
        return True, {}
      if r.status == 422:
        result = await r.json()
        err = Map(result)
        return False, err.errors
      return False, {}

  async def updatePlayer(self, player_id, data):
    payload = {"player": data}
    player_url = "{0}/{1}".format(self.apiUrl("players"), player_id)
    async with self._session.patch(player_url, json=payload) as r:
      if r.status == 200:
        result = await r.json()
        return True, result
      if r.status == 422:
        result = await r.json()
        err = Map(result)
        return False, err.errors
      return False, {}

  # ---------------------------------------------------------------------------
  # DISCORD USER
  # ---------------------------------------------------------------------------

  async def findDiscordUserByDiscordId(self, discord_id):
    request_url = "{api_url}/{discord_id}".format(api_url=self.apiUrl("discord_users"), discord_id=discord_id)
    async with self._session.get(request_url) as response:
      player = await response.json()
      return player if player != [] else None

  # ---------------------------------------------------------------------------
  # GENERAL
  # ---------------------------------------------------------------------------

  async def initCache(self):
    await self.fetchCharactersIfNeeded()

  def unload(self):
    asyncio.create_task(self._session.close())