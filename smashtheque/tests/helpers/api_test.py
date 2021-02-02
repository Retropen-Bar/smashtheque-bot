from   aiohttp import web
import json
import pytest
from   unittest.mock import Mock

from smashtheque.helpers.api import *

# FAKE SERVER

yoshi = {
  "id": 13,
  "name": "Yoshi",
  "emoji": "1234"
}
bowser = {
  "id": 42,
  "name": "Bowser",
  "emoji": "5678"
}
characters = [yoshi, bowser]

rb = {
  "id": 7,
  "short_name": "R-B",
  "name": "Rétropen-Bar"
}
cew = {
  "id": 9,
  "short_name": "CEW",
  "name": "Caramel Ecchi Waysen"
}
teams = [rb, cew]

async def respondWithCharacters(request):
  return web.Response(body=json.dumps(characters), content_type="application/json")
mockCharacters = Mock(side_effect=respondWithCharacters)

async def respondWithTeams(request):
  return web.Response(body=json.dumps(teams), content_type="application/json")
mockTeams = Mock(side_effect=respondWithTeams)

async def respondWithTeam(request):
  return web.Response(body=json.dumps(rb), content_type="application/json")
mockTeam = Mock(side_effect=respondWithTeam)

async def mock500(request):
  return web.Response(status=500)

# TESTS

@pytest.mark.parametrize('test_apiBaseUrl,test_path,expected', [
  (None, "toto", "/api/v1/toto"),
  ("", "toto", "/api/v1/toto"),
  ("https://example.com", None, "https://example.com/api/v1/"),
  ("https://example.com", "", "https://example.com/api/v1/"),
  ("https://example.com", "toto", "https://example.com/api/v1/toto")
])
async def test_apiUrl(test_apiBaseUrl, test_path, expected):
  apiClient = ApiClient(apiBaseUrl=test_apiBaseUrl, bearerToken=None)
  assert apiClient.apiUrl(test_path) == expected

# ---------------------------------------------------------------------------
# CHARACTER
# ---------------------------------------------------------------------------

async def test_fetchCharacters_success(aiohttp_client):
  apiClient = ApiClient(apiBaseUrl=None, bearerToken=None)
  # replace aiohttp ClientSession with a mock
  app = web.Application()
  app.router.add_get('/api/v1/characters', mockCharacters)
  apiClient._session = await aiohttp_client(app)
  # test
  result, data = await apiClient.fetchCharacters()
  assert result
  assert len(data) == 2
  assert apiClient._characters_cache["13"]["name"] == "Yoshi"
  assert apiClient._characters_names_cache["yoshi"] == 13

async def test_fetchCharacters_failure(aiohttp_client):
  apiClient = ApiClient(apiBaseUrl=None, bearerToken=None)
  # replace aiohttp ClientSession with a mock
  app = web.Application()
  app.router.add_get('/api/v1/characters', mock500)
  apiClient._session = await aiohttp_client(app)
  # test
  result, data = await apiClient.fetchCharacters()
  assert result == False
  assert len(data) == 0

async def test_fetchCharactersIfNeeded(aiohttp_client):
  apiClient = ApiClient(apiBaseUrl=None, bearerToken=None)
  # replace aiohttp ClientSession with a mock
  app = web.Application()
  app.router.add_get('/api/v1/characters', mockCharacters)
  apiClient._session = await aiohttp_client(app)
  # check init
  initCallCount = mockCharacters.call_count
  assert len(apiClient._characters_cache) == 0
  # test that data is fetched
  await apiClient.fetchCharactersIfNeeded()
  assert mockCharacters.call_count == initCallCount + 1
  assert len(apiClient._characters_cache) == 2
  # test that data is not fetched a second time and data is still present
  await apiClient.fetchCharactersIfNeeded()
  assert mockCharacters.call_count == initCallCount + 1
  assert len(apiClient._characters_cache) == 2

@pytest.mark.parametrize('emoji_tag,expected_id', [
  (None, None),
  ("", None),
  ("unknown", None),
  ("1234", 13),
  ("5678", 42)
])
async def test_findCharacterByEmojiTag(aiohttp_client, emoji_tag, expected_id):
  apiClient = ApiClient(apiBaseUrl=None, bearerToken=None)
  # replace aiohttp ClientSession with a mock
  app = web.Application()
  app.router.add_get('/api/v1/characters', mockCharacters)
  apiClient._session = await aiohttp_client(app)
  # test
  result = await apiClient.findCharacterByEmojiTag(emoji_tag)
  if expected_id == None:
    assert result == None
  else:
    assert result["id"] == expected_id

@pytest.mark.parametrize('name,expected_id', [
  (None, None),
  ("", None),
  ("unknown", None),
  ("yo shi", 13),
  ("Bôwser", 42),
  ("bowser", 42)
])
async def test_findCharacterByName(aiohttp_client, name, expected_id):
  apiClient = ApiClient(apiBaseUrl=None, bearerToken=None)
  # replace aiohttp ClientSession with a mock
  app = web.Application()
  app.router.add_get('/api/v1/characters', mockCharacters)
  apiClient._session = await aiohttp_client(app)
  # test
  result = await apiClient.findCharacterByName(name)
  if expected_id == None:
    assert result == None
  else:
    assert result["id"] == expected_id

@pytest.mark.parametrize('label,expected_id', [
  (None, None),
  ("", None),
  ("unknown", None),
  ("<:placeholder:666>", None),
  ("<:placeholder:1234>", 13),
  ("Bôwser", 42),
  ("bowser", 42)
])
async def test_findCharacterByLabel(aiohttp_client, label, expected_id):
  apiClient = ApiClient(apiBaseUrl=None, bearerToken=None)
  # replace aiohttp ClientSession with a mock
  app = web.Application()
  app.router.add_get('/api/v1/characters', mockCharacters)
  apiClient._session = await aiohttp_client(app)
  # test
  result = await apiClient.findCharacterByLabel(label)
  if expected_id == None:
    assert result == None
  else:
    assert result["id"] == expected_id

@pytest.mark.parametrize('label,expected', [
  (None, False),
  ("", False),
  ("unknown", False),
  ("<:placeholder:666>", False),
  ("<:placeholder:1234>", False),
  ("Bôwser", True),
  ("bowser", True)
])
async def test_isCharacterName(aiohttp_client, label, expected):
  apiClient = ApiClient(apiBaseUrl=None, bearerToken=None)
  # replace aiohttp ClientSession with a mock
  app = web.Application()
  app.router.add_get('/api/v1/characters', mockCharacters)
  apiClient._session = await aiohttp_client(app)
  # test
  result = await apiClient.isCharacterName(label)
  assert result == expected

@pytest.mark.parametrize('label,expected', [
  (None, False),
  ("", False),
  ("unknown", False),
  ("<:placeholder:666>", False),
  ("<:placeholder:1234>", True),
  ("Bôwser", True),
  ("bowser", True)
])
async def test_isCharacter(aiohttp_client, label, expected):
  apiClient = ApiClient(apiBaseUrl=None, bearerToken=None)
  # replace aiohttp ClientSession with a mock
  app = web.Application()
  app.router.add_get('/api/v1/characters', mockCharacters)
  apiClient._session = await aiohttp_client(app)
  # test
  result = await apiClient.isCharacter(label)
  assert result == expected

# ---------------------------------------------------------------------------
# TEAM
# ---------------------------------------------------------------------------

async def test_findTeamByShortName(aiohttp_client):
  apiClient = ApiClient(apiBaseUrl=None, bearerToken=None)
  # replace aiohttp ClientSession with a mock
  app = web.Application()
  app.router.add_get('/api/v1/teams', mockTeams)
  apiClient._session = await aiohttp_client(app)
  # test
  initCallCount = mockTeams.call_count
  result, details = await apiClient.findTeamByShortName('toto')
  assert mockTeams.call_count == initCallCount + 1
  assert len(apiClient._teams_cache) == 2
  assert apiClient._teams_cache["7"]["name"] == "Rétropen-Bar"
  assert result
  assert details["id"] == 7

async def test_findTeamById(aiohttp_client):
  apiClient = ApiClient(apiBaseUrl=None, bearerToken=None)
  # replace aiohttp ClientSession with a mock
  app = web.Application()
  app.router.add_get('/api/v1/teams/7', mockTeam)
  apiClient._session = await aiohttp_client(app)
  # test
  initCallCount = mockTeam.call_count
  result, details = await apiClient.findTeamById(7)
  assert mockTeam.call_count == initCallCount + 1
  assert result
  assert details["short_name"] == "R-B"

async def test_updateTeam(aiohttp_client):
  apiClient = ApiClient(apiBaseUrl=None, bearerToken=None)
  # replace aiohttp ClientSession with a mock
  app = web.Application()
  app.router.add_patch('/api/v1/teams/7', mockTeam)
  apiClient._session = await aiohttp_client(app)
  # test
  initCallCount = mockTeam.call_count
  result, details = await apiClient.updateTeam(7, {})
  assert mockTeam.call_count == initCallCount + 1
  assert result

# -----------------------------------------------------------------------------
# TOURNAMENT
# -----------------------------------------------------------------------------

#   async def findTournamentById(self, tournament_id):
#     request_url = f"{self.apiUrl('recurring_tournaments')}/{tournament_id}"
#     async with self._session.get(request_url) as response:
#       tournament = await response.json()
#       return tournament

#   async def createTournamentEvent(self, data):
#     payload = {"tournament_event": data}
#     request_url = self.api_url("tournament_events")
#     async with self._session.post(request_url, json=payload) as r:
#       if r.status == 201:
#         return True, 'created'
#       if r.status == 200:
#         return True, 'updated'
#       if r.status == 422:
#         result = await r.json()
#         err = Map(result)
#         return False, err.errors
#       return False, {}

#   # ---------------------------------------------------------------------------
#   # LOCATION
#   # ---------------------------------------------------------------------------

#   async def findLocationByName(self, name):
#     request_url = "{0}?by_name_like={1}".format(self.apiUrl("locations"), name)
#     async with self._session.get(request_url) as response:
#       locations = await response.json()
#       if locations != []:
#         # puts values in cache before responding
#         for location in locations:
#           self._locations_cache[str(location["id"])] = location
#         return locations[0]
#       else:
#         return None

#   async def createLocation(self, name, country=False):
#     payload = {"name": name}
#     if country:
#       payload["type"] = "Locations::Country"
#     async with self._session.post(self.apiUrl("locations"), json=payload) as r:
#       if r.status == 201:
#         # location creation went fine
#         return True, {}
#       if r.status == 422:
#         result = await r.json()
#         err = Map(result)
#         return False, err.errors
#       return False, {}

#   # ---------------------------------------------------------------------------
#   # PLAYER
#   # ---------------------------------------------------------------------------

#   async def findPlayerById(self, player_id):
#     request_url = "{0}/{1}".format(self.apiUrl("players"), player_id)
#     async with self._session.get(request_url) as response:
#       player = await response.json()
#       return player

#   async def findPlayerByIds(self, player_ids):
#     players = []
#     for player_id in player_ids:
#       player = await self.findPlayerById(player_id)
#       players.append(player)
#     return players

#   async def findPlayerByDiscordId(self, discord_id):
#     request_url = "{0}?by_discord_id={1}".format(self.apiUrl("players"), discord_id)
#     async with self._session.get(request_url) as response:
#       players = await response.json()
#       if len(players) > 0:
#         return players[0]
#       return None

#   async def findPlayersByNameLike(self, name):
#     request_url = "{0}?by_name_like={1}".format(self.apiUrl("players"), name)
#     async with self._session.get(request_url) as response:
#       players = await response.json()
#       return players

#   async def createPlayer(self, player):
#     payload = {"player": player}
#     async with self._session.post(self.apiUrl("players"), json=payload) as r:
#       if r.status == 201:
#         return True, {}
#       if r.status == 422:
#         result = await r.json()
#         err = Map(result)
#         return False, err.errors
#       return False, {}

#   async def updatePlayer(self, player_id, data):
#     payload = {"player": data}
#     player_url = "{0}/{1}".format(self.apiUrl("players"), player_id)
#     async with self._session.patch(player_url, json=payload) as r:
#       if r.status == 200:
#         result = await r.json()
#         return True, result
#       if r.status == 422:
#         result = await r.json()
#         err = Map(result)
#         return False, err.errors
#       return False, {}

#   # ---------------------------------------------------------------------------
#   # DISCORD USER
#   # ---------------------------------------------------------------------------

#   async def findDiscordUserByDiscordId(self, discord_id):
#     request_url = "{api_url}/{discord_id}".format(api_url=self.apiUrl("discord_users"), discord_id=discord_id)
#     async with self._session.get(request_url) as response:
#       player = await response.json()
#       return player if player != [] else None

#   # ---------------------------------------------------------------------------
#   # GENERAL
#   # ---------------------------------------------------------------------------

#   async def initCache(self):
#     await self.fetchCharactersIfNeeded()

#   def unload(self):
#     asyncio.create_task(self._session.close())
