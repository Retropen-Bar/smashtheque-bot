import aiohttp

import misc

class ApiClient:

  def __init__(self, apiBaseUrl, bearerToken):
    self.apiBaseUrl = apiBaseUrl
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
    return f"{self.apiBaseUrl}/api/v1/{collection}"

  # ---------------------------------------------------------------------------
  # CHARACTERS
  # ---------------------------------------------------------------------------

  async def fetchCharacters(self):
    async with self._session.get(self.apiUrl("characters")) as response:
      characters = await response.json()
      # puts values in cache before responding
      for character in characters:
        self._characters_cache[str(character["id"])] = character
        self._characters_names_cache[normalize_str(character["name"])] = character["id"]
      # respond
      return characters

  async def fetchCharactersIfNeeded(self):
    if len(self._characters_cache) < 1 or len(self._characters_names_cache) < 1:
      await self.fetchCharacters()

  async def findCharacterByEmojiTag(self, emoji):
    found = re.search(r"[0-9]+", emoji)
    if found == None:
      return None
    emoji_id = found.group()
    for character_id in self._characters_cache:
      character = self._characters_cache[str(character_id)]
      if character["emoji"] == emoji_id:
        return character
    return None

  # this method is called when we are sure @name exists as a key of @_characters_names_cache
  async def findCharacterByName(self, name):
    character_id = self._characters_names_cache[normalize_str(name)]
    return self._characters_cache[str(character_id)]

  async def findCharacterByLabel(self, label):
    # fill characters cache if empty
    await self.fetchCharactersIfNeeded()

    if is_emoji(label):
      character = await self.findCharacterByEmojiTag(label)
      if character == None:
        return None
      return character

    if self.is_character_name(label):
      character = await self.findCharacterByName(label)
      if character == None:
        return None
      return character

    return None

  def isCharacterName(self, v):
    return normalize_str(v) in self._characters_names_cache

  def isCharacter(self, v):
    return is_emoji(v) or self.isCharacterName(v)

  # ---------------------------------------------------------------------------
  # GENERAL
  # ---------------------------------------------------------------------------

  async def initCache(self):
    await self.fetchCharactersIfNeeded()
