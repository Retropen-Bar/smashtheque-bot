from redbot.core import commands
from redbot.core.utils.predicates import ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.chat_formatting import humanize_list
import discord
import asyncio
import aiohttp
from redbot.core.bot import Red
from typing import Optional
import re
import json
import math
import rollbar
import os
import sys
import unicodedata
from collections.abc import Mapping
from collections import UserDict
from random import choice

def normalize_str(s):
    s1 = ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )
    s2 = re.sub("[^a-zA-Z]+", "", s1)
    return s2.lower()

async def yeet(ctx, erreur):
    """lever des erreurs"""
    embed = discord.Embed(
        title=f"Erreur dans la commande {ctx.command} :",
        description=erreur,
        colour=discord.Colour.red()
    )
    embed.set_author(
        name="Smashthèque",
        icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
    )
    await ctx.send(embed=embed)

async def uniqueyeet(ctx, erreur, playername):
    """lever des erreurs en ajoutant le nom du joueur"""
    global failed_lines
    failed_lines.append(playername)
    embed = discord.Embed(
        title=f"Erreur pendant le traitement de la ligne {playername} :",
        description=erreur,
        colour=discord.Colour.red()
    )
    embed.set_author(
        name="Smashthèque",
        icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
    )
    await ctx.send(embed=embed)

async def generic_error(ctx, error):
    await yeet(ctx, "T'as cassé le bot, GG. Tu peux contacter <@332894758076678144> ou <@608210202952466464> s'il te plaît ?")
    rollbar.report_exc_info(sys.exc_info(), error)

def loop_dict(dict_to_use, value, parameter):
    """trouver une entrée dans un dictionnaire"""
    for sub in dict_to_use:
        if sub[value] == parameter:
            return sub

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

def is_discord_id(v):
    return v.isdigit() and (len(str(v)) == 17 or len(str(v)) == 18)

def is_emoji(v):
    return re.search(r"<a?:(\w+):(\d+)>", v) != None

class Map(UserDict):
    def __getattr__(self, attr):
        val = self.data[attr]
        if isinstance(val, Mapping):
            return Map(val)
        return val

class Error(Exception):
    """Base class for other exceptions"""
    pass

class CharactersCacheNotFetched(Error):
    """Raised when the cache is not fetched yet"""
    pass


class Smashtheque(commands.Cog):
    async def initialize(self):
        if 'ROLLBAR_TOKEN' in os.environ and os.environ['ROLLBAR_TOKEN']:
            rollbar_token = os.environ['ROLLBAR_TOKEN']
            if 'ROLLBAR_ENV' in os.environ and os.environ['ROLLBAR_ENV']:
                rollbar_env = os.environ['ROLLBAR_ENV']
            else:
                rollbar_env = 'production'

        else:
            rollbar_token = await self.bot.get_shared_api_tokens("smashtheque")
            rollbar_token = rollbar_token["token"]
            if 'environment' in rollbar_token:
                rollbar_env = rollbar_token["environment"]
            else:
                rollbar_env = 'production'
        rollbar.init(rollbar_token, rollbar_env)

        try:
            if 'SMASHTHEQUE_API_URL' in os.environ and os.environ['SMASHTHEQUE_API_URL']:
                self.api_base_url = os.environ['SMASHTHEQUE_API_URL']
            else:
                api_base_url = await self.bot.get_shared_api_tokens("smashtheque")
                self.api_base_url = api_base_url["url"]
            print(f"Smashthèque API base URL set to {self.api_base_url}")
            if 'SMASHTHEQUE_API_TOKEN' in os.environ and os.environ['SMASHTHEQUE_API_TOKEN']:
                bearer = os.environ['SMASHTHEQUE_API_TOKEN']
            else:
                bearer = await self.bot.get_shared_api_tokens("smashtheque")
                bearer = bearer["bearer"]
            headers = {
                "Authorization": f"Bearer {bearer}",
                "Content-Type": "application/json",
            }
            self._session = aiohttp.ClientSession(headers=headers)
            self._characters_cache = {}
            self._characters_names_cache = {}
            self._locations_cache = {}
            self._teams_cache = {}
        except:
            rollbar.report_exc_info()
            raise

    def __init__(self, bot: Red):
        self.bot = bot

    def cog_unload(self):
        asyncio.create_task(self._session.close())

    def api_url(self, collection):
        return f"{self.api_base_url}/api/v1/{collection}"

    def is_character_name(self, v):
        return normalize_str(v) in self._characters_names_cache

    def is_character(self, v):
        return is_emoji(v) or self.is_character_name(v)

    async def fetch_characters(self):
        print('fetch_characters')
        async with self._session.get(self.api_url("characters")) as response:
            characters = await response.json()
            # puts values in cache before responding
            for character in characters:
                self._characters_cache[str(character["id"])] = character
                self._characters_names_cache[normalize_str(character["name"])] = character["id"]
            # respond
            return characters

    async def fetch_characters_if_needed(self):
        print('fetch_characters_if_needed')
        if len(self._characters_cache) < 1 or len(self._characters_names_cache) < 1:
            await self.fetch_characters()

    async def find_character_by_label(self, ctx, label):

        # fill characters cache if empty
        await self.fetch_characters_if_needed()

        if is_emoji(label):
            character = await self.find_character_by_emoji_tag(ctx, label)
            return character

        if self.is_character_name(label):
            character = await self.find_character_by_name(ctx, label)
            return character

        await yeet(ctx, f"Perso {label} non reconnu")
        return None

    async def find_character_by_emoji_tag(self, ctx, emoji):
        found = re.search(r"[0-9]+", emoji)
        if found == None:
            await yeet(
                ctx,
                f"Emoji {emoji} non reconnu : veuillez utiliser les émojis de personnages de la Smashthèque ou utiliser un nom de personnage."
            )
            return None
        emoji_id = found.group()
        for character_id in self._characters_cache:
            character = self._characters_cache[str(character_id)]
            if character["emoji"] == emoji_id:
                return character
        await yeet(
            ctx,
            f"Emoji {emoji} non reconnu : veuillez utiliser les émojis de personnages de la Smashthèque ou utiliser un nom de personnage."
        )
        return None

    # this method is called when we are sure @name exists as a key of @_characters_names_cache
    async def find_character_by_name(self, ctx, name):
        character_id = self._characters_names_cache[normalize_str(name)]
        return self._characters_cache[str(character_id)]

    async def find_team_by_short_name(self, short_name):
        request_url = "{0}?by_short_name_like={1}".format(self.api_url("teams"), short_name)
        async with self._session.get(request_url) as response:
            teams = await response.json()
            if teams != []:
                # puts values in cache before responding
                for team in teams:
                    self._teams_cache[str(team["id"])] = team
                return teams[0]
            else:
                return None

    async def find_team_by_id(self, team_id):
        request_url = "{api_url}/{team_id}".format(api_url=self.api_url("teams"), team_id=team_id)
        async with self._session.get(request_url) as response:
            team = await response.json()
            return team #or team[0]

    async def find_location_by_name(self, name):
        request_url = "{0}?by_name_like={1}".format(self.api_url("locations"), name)
        async with self._session.get(request_url) as response:
            locations = await response.json()
            if locations != []:
                # puts values in cache before responding
                for location in locations:
                    self._locations_cache[str(location["id"])] = location
                return locations[0]
            else:
                return None

    async def find_player_by_id(self, player_id):
        request_url = "{0}/{1}".format(self.api_url("players"), player_id)
        async with self._session.get(request_url) as response:
            player = await response.json()
            return player

    async def find_player_by_ids(self, player_ids):
        players = []
        for player_id in player_ids:
            player = await self.find_player_by_id(player_id)
            players.append(player)
        return players

    async def find_player_by_discord_id(self, discord_id):
        request_url = "{0}?by_discord_id={1}".format(self.api_url("players"), discord_id)
        async with self._session.get(request_url) as response:
            players = await response.json()
            if len(players) > 0:
                return players[0]
            return None

    async def find_players_by_name_like(self, name):
        request_url = "{0}?by_name_like={1}".format(self.api_url("players"), name)
        async with self._session.get(request_url) as response:
            players = await response.json()
            return players

    async def find_member_by_discord_id(self, discord_id):
        request_url = "{api_url}/{discord_id}".format(api_url=self.api_url("discord_users"), discord_id=discord_id)
        async with self._session.get(request_url) as response:
            player = await response.json()
            return player if player != [] else None

    async def raise_message(self, ctx, message):
        embed = discord.Embed(title=message)
        embed.set_author(
            name="Smashthèque",
            icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
        )
        await ctx.send(embed=embed)

    async def raise_not_linked(self, ctx):
        await self.raise_message(ctx, f"Votre compte Discord n'est associé à aucun joueur.\nUtilisez `{ctx.clean_prefix}jesuis` pour associer votre compte à un joueur.")

    async def ask_confirmation(self, ctx, embed):
        temp_message = await ctx.send(embed=embed)
        pred = ReactionPredicate.yes_or_no(temp_message, ctx.author)
        start_adding_reactions(
            temp_message, ReactionPredicate.YES_OR_NO_EMOJIS
        )
        try:
            await self.bot.wait_for("reaction_add", timeout=60.0, check=pred)
        except asyncio.TimeoutError:
            await ctx.send("Commande annulée")
            return False
        if pred.result is True:
            await temp_message.delete()
            return True
        else:
            await ctx.send("Commande annulée")
            await temp_message.delete()
            return False

    async def ask_choice(self, ctx, embed, elements_count):
        temp_message = await ctx.send(embed=embed)
        emojis = ReactionPredicate.NUMBER_EMOJIS[1:elements_count + 1]
        start_adding_reactions(temp_message, emojis)
        pred = ReactionPredicate.with_emojis(emojis, temp_message)
        try:
            await ctx.bot.wait_for("reaction_add", timeout=60.0, check=pred)
        except asyncio.TimeoutError:
            await ctx.send("Commande annulée")
            return None
        if type(pred.result) == int:
            await temp_message.delete()
            return pred.result
        return None

    async def show_confirmation(self, ctx, message):
        embed = discord.Embed(
            title="I guess it's done!",
            description=message,
            colour=discord.Colour.green()
        )
        await ctx.send(embed=embed)

    def embed_players(self, embed, players, with_index=False):
        idx = 0
        for player in players:
            if idx > 0:
                embed.add_field(name="\u200b", value="\u200b", inline=False)
            self.embed_player(embed, player, with_index=with_index, index=idx+1)
            idx += 1

    def embed_player(self, embed, _player, with_index=False, index=0):
        player = Map(_player)

        personnages = []
        if "characters" in _player:
            for character in player.characters:
                personnages.append(format_character(character))
        elif "character_ids" in _player:
            for character_id in player.character_ids:
                personnages.append(format_character(self._characters_cache[str(character_id)]))
        if len(personnages) < 1:
            personnages.append("\u200b")

        player_name = player.name
        if with_index:
            player_name = ReactionPredicate.NUMBER_EMOJIS[index] + " " + player_name
        embed.add_field(name=player_name, value="".join(personnages), inline=True)

        team_names = []
        if "teams" in _player:
            for team in player.teams:
                team_names.append(format_team(team))
        elif "team_ids" in _player:
            for team_id in player.team_ids:
                team_names.append(format_team(self._teams_cache[str(team_id)]))
        if len(team_names) > 0:
            embed.add_field(name="Équipes", value="\n".join(team_names), inline=True)

        location_names = []
        if "locations" in _player:
            for location in player.locations:
                location_names.append(format_location(location))
        elif "location_ids" in _player:
            for location_id in player.location_ids:
                location_names.append(format_location(self._locations_cache[str(location_id)]))
        if len(location_names) > 0:
            embed.add_field(name="Localisations", value="\n".join(location_names), inline=True)

        if "discord_id" in _player and player.discord_id != None:
            discord_user = format_discord_user(player.discord_id)
            embed.add_field(name="Compte Discord", value=discord_user, inline=True)

    async def confirm_create_player(self, ctx, player):
        embed = discord.Embed(
            title="Vous allez créer le joueur suivant :",
            colour=discord.Colour.blue(),
        )
        embed.set_footer(text="Réagissez avec ✅ pour confirmer et créer ce joueur, ou réagissez avec ❎ pour annuler.")
        self.embed_player(embed, player)
        doit = await self.ask_confirmation(ctx, embed)
        if doit:
            await self.create_player(ctx, player)

    async def create_player(self, ctx, player):
        print(f"create player {player}")
        payload = {"player": player}
        async with self._session.post(self.api_url("players"), json=payload) as r:
            if r.status == 201:
                # player creation wen fine
                player_name = player["name"]
                await self.show_confirmation(ctx, f"Le joueur {player_name} a été ajouté à la Smashthèque et est en attente de validation.")
                return

            if r.status == 422:
                result = await r.json()
                erreur = Map(result)
                print(f"errors: {erreur.errors}")
                if "name" in erreur.errors and erreur.errors["name"] == "already_known":
                    alts = await self.find_player_by_ids(erreur.errors["existing_ids"])
                    embed = discord.Embed(
                        title="Un ou plusieurs joueurs possèdent le même pseudo que le joueur que vous souhaitez ajouter.",
                        colour=discord.Colour.blue()
                    )
                    embed.set_footer(text="Réagissez avec ✅ pour confirmer et créer un nouveau joueur, ou\nréagissez avec ❎ pour annuler.")
                    self.embed_players(embed, alts)
                    doit = await self.ask_confirmation(ctx, embed)
                    if doit:
                        player["name_confirmation"] = True
                        await self.create_player(ctx, player)
                elif "discord_user" in erreur.errors and erreur.errors["discord_user"] == ["already_taken"]:
                    await yeet(ctx, "Ce compte Discord est déjà relié à un autre joueur dans la Smashthèque.")
                    return
                else:
                    await generic_error(ctx, erreur)
                    return

    async def update_player(self, ctx, player_id, data):
        print(f"update player {player_id} with {data}")
        payload = {"player": data}
        player_url = "{0}/{1}".format(self.api_url("players"), player_id)
        async with self._session.patch(player_url, json=payload) as r:
            if r.status == 200:
                embed = discord.Embed(title="Joueur mis à jour :")
                self.embed_player(embed, await r.json())
                await ctx.send(embed=embed)
                return

            if r.status == 422:
                result = await r.json()
                erreur = Map(result)
                print(f"errors: {erreur.errors}")
                if "name" in erreur.errors and erreur.errors["name"] == "already_known":
                    alts = await self.find_player_by_ids(erreur.errors["existing_ids"])
                    embed = discord.Embed(
                        title="Un ou plusieurs autres joueurs utilisent ce pseudo.",
                        colour=discord.Colour.blue()
                    )
                    embed.set_footer(text="Réagissez avec ✅ pour confirmer et mettre à jour, ou\nréagissez avec ❎ pour annuler.")
                    self.embed_players(embed, alts)
                    doit = await self.ask_confirmation(ctx, embed)
                    if doit:
                        data["name_confirmation"] = True
                        await self.update_player(ctx, player_id, data)
                elif "discord_user" in erreur.errors and erreur.errors["discord_user"] == ["already_taken"]:
                    await yeet(ctx, "Ce compte Discord est déjà relié à un autre joueur dans la Smashthèque.")
                    return
                else:
                    await generic_error(ctx, erreur)
                    return

    async def do_createlocation(self, ctx, name, country=False):
        print(f"create location {name}")
        payload = {"name": name}
        if country:
            payload["type"] = "Locations::Country"
        async with self._session.post(self.api_url("locations"), json=payload) as r:
            if r.status == 201:
                # location creation went fine
                await self.show_confirmation(ctx, f"La localisation {name} a été ajoutée à la base de données.")
                return

            if r.status == 422:
                result = await r.json()
                erreur = Map(result)
                print(erreur.errors["name"])
                if erreur.errors["name"] == ["not_unique"]:
                    await yeet(ctx, "Cette localisation existe déjà dans la Smashthèque.")
                    return

            # something went wrong but we don't know what
            await generic_error(ctx, r)
            return

    async def do_addplayer(self, ctx, arg):

        # fill characters cache if empty
        await self.fetch_characters_if_needed()

        # stages:
        # 0: pseudo
        # 1: characters
        # 2: team
        # 3: location
        # 4: discord ID

        current_stage = 0

        # init de la réponse
        response = {
            "name": "",
            "character_ids": [],
            "creator_discord_id": "",
            "location_ids": [],
            "team_ids": []
        }

        # process each argument between spaces
        # [name piece] [name piece] [emoji] [emoji] [team] [location] [discord ID]
        arguments = arg.split()

        for argu in arguments:
            print(f"current_stage={current_stage} argu={argu}")

            if current_stage == 0:
                print('stage 0')
                # at this stage, the next argument could be a name piece
                # ... [name piece] [emoji] [emoji] [team] [location] [discord ID]

                if self.is_character(argu):
                    if len(response["name"]) > 0:
                        # we are actually done with the name, so go to stage 1
                        current_stage = 1
                        # do not 'continue' here because we stil want to process @argu
                    else:
                        await yeet(
                            ctx, "Veuillez commencer par donner le pseudo du joueur."
                        )
                        return
                else:
                    # parse le nom qui peut contenir des espaces
                    response["name"] = response["name"] + argu + " "
                    # there could still be remaining pieces of the pseudo,
                    # so do not go to stage 1 yet
                    continue

            # do not use elif here because we want the previous section to be able to go here
            # without restarting the loop
            if current_stage == 1:
                print('stage 1')
                # at this stage, the next argument could be a character emoji
                # ... [emoji] [emoji] [team] [location] [discord ID]

                if not self.is_character(argu):
                    # we are actually done with the emojis, so go to stage 2
                    current_stage = 2
                    # do not 'continue' here because we stil want to process @argu
                else:
                    # more emojis to parse
                    character = await self.find_character_by_label(ctx, argu)
                    if character == None:
                        return
                    response["character_ids"].append(character["id"])
                    # there could still be emojis to parse,
                    # so do not go to stage 2 yet
                    continue

            # do not use elif here because we want the previous section to be able to go here
            # without restarting the loop
            if current_stage == 2:
                print('stage 2')
                # at this stage, the next argument could be a team
                # ... [team] [location] [discord ID]

                if is_discord_id(argu):
                    response["discord_id"] = str(argu)
                    break

                team = await self.find_team_by_short_name(argu)
                if team != None:
                    response["team_ids"].append(team["id"])
                    current_stage = 3
                    continue

                # nope, not a team, try next stage
                current_stage = 3

            # do not use elif here because we want the previous section to be able to go here
            # without restarting the loop
            if current_stage == 3:
                print('stage 3')
                # at this stage, the next argument could be a location
                # ... [location] [discord ID]

                if is_discord_id(argu):
                    response["discord_id"] = str(argu)
                    break

                location = await self.find_location_by_name(argu)
                if location != None:
                    response["location_ids"].append(location["id"])
                    current_stage = 4
                    continue

                # nope, not a location
                # so we have a problem here
                # because argu is neither a location nor a Discord ID
                # -> we could already stop here and raise an issue

                current_stage = 4

            # do not use elif here because we want the previous section to be able to go here
            # without restarting the loop
            if current_stage == 4:
                print('stage 4')
                # at this stage, the next argument could only be a discord ID
                # ... [discord ID]

                if is_discord_id(argu):
                    response["discord_id"] = str(argu)
                    break

                # so we were unable to parse argu
                if len(response["location_ids"]) > 0:
                    # we have a location, so we are pretty sure argu was supposed to be a Discord ID
                    await yeet(
                        ctx,
                        f"Veuillez entrer un ID Discord correct pour le joueur à ajouter : {argu} n'en est pas un.\nPour avoir l'ID d'un utilisateur, activez simplement les options de développeur dans l'onglet apparence de discord, puis faites un clic droit sur l'utilisateur > copier l'identifiant."
                    )
                    return
                elif len(response["team_ids"]) > 0:
                    # we have a team, so argu could be for a location or a Discord ID
                    await yeet(
                        ctx,
                        f"Nous n'avons pas réussi à reconnaître {argu}.\nS'il s'agit d'une localisation (ville, pays), vous pouvez la créer avec `{ctx.clean_prefix}creerville` ou `{ctx.clean_prefix}creerpays`.\nS'il s'agit d'un ID Discord, il n'est pas correct\nPour avoir l'ID d'un utilisateur, activez simplement les options de développeur dans l'onglet apparence de discord, puis faites un clic droit sur l'utilisateur > copier l'identifiant."
                    )
                    return
                else:
                    # we have no team and no location: argu could be for a team, a location or a Discord ID
                    await yeet(
                        ctx,
                        f"Nous n'avons pas réussi à reconnaître {argu}.\nS'il s'agit d'une équipe, vous devez demander à un administrateur de la créer.\nS'il s'agit d'une localisation (ville, pays), vous pouvez la créer avec `{ctx.clean_prefix}creerville` ou `{ctx.clean_prefix}creerpays`.\nS'il s'agit d'un ID Discord, il n'est pas correct\nPour avoir l'ID d'un utilisateur, activez simplement les options de développeur dans l'onglet apparence de discord, puis faites un clic droit sur l'utilisateur > copier l'identifiant."
                    )
                    return


        # make sure some characters were provided
        if len(response["character_ids"]) < 1:
            await yeet(
                ctx, "Vous n'avez précisé aucun personnage joué ! C'est obligatoire."
            )
            return

        # now the player is filled with attributes
        response["creator_discord_id"] = str(ctx.author.id)
        response["name"] = response["name"].rstrip()
        await self.confirm_create_player(ctx, response)

    async def do_link(self, ctx, pseudo, discord_id):
        player = await self.find_player_by_discord_id(discord_id)
        if player != None:
            embed = discord.Embed(title="Un joueur est déjà associé à ce compte Discord. Contactez un admin pour dissocier ce compte Discord de ce joueur.")
            self.embed_player(embed, player)
            await ctx.send(embed=embed)
            return

        players = await self.find_players_by_name_like(pseudo)

        # no player found
        if len(players) == 0:
            await self.raise_message(ctx, f"Ce pseudo n'existe pas.\nUtilisez la commande `{ctx.clean_prefix}creerjoueur` pour l'ajouter.\n")
            return

        # one player found: ask confirmation
        if len(players) == 1:
            player = players[0]
            embed = discord.Embed(
                title="Joueur trouvé :",
                colour=discord.Colour.blue()
            )
            self.embed_player(embed, player)
            doit = await self.ask_confirmation(ctx, embed)
            if not doit:
                return
            if player["discord_id"] != None:
                await self.raise_message(ctx, "Il semblerait que ce joueur soit déjà associé à un compte Discord")
                return
            await self.update_player(ctx, player["id"], {"discord_id": str(discord_id)})
            discord_user = format_discord_user(discord_id)
            await self.show_confirmation(ctx, f"Le compte Discord {discord_user} est maintenant associé au joueur {pseudo}.")
            return

        # multiple players found: ask which one
        embed = discord.Embed(
            title="Plusieurs joueurs ont ce pseudo.\nChoisissez le bon joueur dans la liste ci-dessous grâce aux réactions",
            colour=discord.Colour.blue()
        )
        self.embed_players(embed, players, with_index=True)
        choice = await self.ask_choice(ctx, embed, len(players))
        player = players[choice]
        if player["discord_id"] != None:
            await self.raise_message(ctx, "Il semblerait que ce joueur soit déjà associé à un compte Discord")
            return
        await self.update_player(ctx, player["id"], {"discord_id": str(discord_id)})
        discord_user = format_discord_user(discord_id)
        await self.show_confirmation(ctx, f"Le compte Discord {discord_user} est maintenant associé au joueur {pseudo}.")

    async def do_unlink(self, ctx, target_member):
        discord_id = target_member.id
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        embed = discord.Embed(title="Un joueur est associé à ce compte discord. Voulez vous le dissocier ?")
        embed.set_footer(text="Réagissez avec ✅ pour confirmer et dissocier ce compte du joueur, ou\nréagissez avec ❎ pour annuler.")
        self.embed_player(embed, player)
        doit = await self.ask_confirmation(ctx, embed)
        if not doit:
            return
        await self.update_player(ctx, player["id"], {"discord_id": None})
        player_name = player["name"]
        discord_user = format_discord_user(discord_id)
        await self.show_confirmation(ctx, f"Le compte Discord {discord_user} a été dissocié du joueur {player_name}.")

    async def do_showplayer(self, ctx, target_member):
        discord_id = target_member.id
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        embed = discord.Embed(
            title="Ce compte Discord est associé au joueur suivant :",
            colour=discord.Colour.green(),
        )
        self.embed_player(embed, player)
        await ctx.send(embed=embed)

    async def do_findplayer(self, ctx, name):
        players = await self.find_players_by_name_like(name)

        # no player found
        if len(players) == 0:
            await self.raise_message(ctx, f"Aucun joueur connu avec ce pseudo.\nVous pouvez utiliser la commande `{ctx.clean_prefix}creerjoueur` pour ajouter un joueur.\n")
            return

        if len(players) == 1:
            player = players[0]
            embed = discord.Embed(
                title="Joueur trouvé :",
                colour=discord.Colour.green()
            )
            self.embed_player(embed, player)
        else:
            embed = discord.Embed(
                title="Plusieurs joueurs ont ce pseudo :",
                colour=discord.Colour.green()
            )
            self.embed_players(embed, players)
        await ctx.send(embed=embed)
        return

    async def do_editname(self, ctx, discord_id, new_name):
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        await self.update_player(ctx, player["id"], {"name": new_name})

    async def do_removelocation(self, ctx, discord_id, location_name):
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        location_ids = player["location_ids"]
        location = await self.find_location_by_name(location_name)
        if location == None:
            await self.raise_message(
                ctx,
                f"Nous n'avons pas réussi à trouver {location_name}.\nS'il s'agit d'une ville, vous pouvez l'ajouter à la Smashthèque avec `{ctx.clean_prefix}creerville`.\nS'il s'agit d'un pays, vous pouvez l'ajouter à la Smashthèque avec `{ctx.clean_prefix}creerpays`"
            )
            return
        location_id = location["id"]
        if location_id in location_ids:
            location_ids.remove(location_id)
        await self.update_player(ctx, player["id"], {"location_ids": location_ids})

    async def do_addlocation(self, ctx, discord_id, location_name):
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        location_ids = player["location_ids"]
        location = await self.find_location_by_name(location_name)
        if location == None:
            await self.raise_message(
                ctx,
                f"Nous n'avons pas réussi à trouver {location_name}.\nS'il s'agit d'une ville, vous pouvez l'ajouter à la Smashthèque avec `{ctx.clean_prefix}creerville`.\nS'il s'agit d'un pays, vous pouvez l'ajouter à la Smashthèque avec `{ctx.clean_prefix}creerpays`."
            )
            return
        location_id = location["id"]
        if location_id in location_ids:
            await self.raise_message(
                ctx,
                f"Ce joueur est déjà localisé à {location_name}."
            )
            return
        location_ids.append(location_id)
        await self.update_player(ctx, player["id"], {"location_ids": location_ids})

    async def do_removeteam(self, ctx, discord_id, team_short_name):
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        team_ids = player["team_ids"]
        team = await self.find_team_by_short_name(team_short_name)
        if team == None:
            await self.raise_message(
                ctx,
                f"Nous n'avons pas réussi à trouver l'équipe {team_short_name}.\nVous pouvez demander à un administrateur de la créer."
            )
            return
        team_id = team["id"]
        if team_id in team_ids:
            team_ids.remove(team_id)
        await self.update_player(ctx, player["id"], {"team_ids": team_ids})

    async def do_addteam(self, ctx, discord_id, team_short_name):
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        team_ids = player["team_ids"]
        team = await self.find_team_by_short_name(team_short_name)
        if team == None:
            await self.raise_message(
                ctx,
                f"Nous n'avons pas réussi à trouver l'équipe {team_short_name}.\nVous pouvez demander à un administrateur de la créer."
            )
            return
        team_id = team["id"]
        if team_id in team_ids:
            await self.raise_message(
                ctx,
                f"Ce joueur est déjà membre de l'équipe {team_short_name}."
            )
            return
        team_ids.append(team_id)
        await self.update_player(ctx, player["id"], {"team_ids": team_ids})

    async def do_listavailablecharacters(self, ctx):

        # fill characters cache if empty
        await self.fetch_characters_if_needed()

        lines = []
        for character_id in self._characters_cache:
            character = self._characters_cache[str(character_id)]
            tag = format_character(character)
            name = character["name"]
            lines.append([tag, name])
        lines.sort(key=lambda l: l[1])
        for idx in range(0, len(lines)):
            lines[idx] = " ".join(lines[idx])

        parts = math.ceil(len(lines) / 30)
        part = 0
        for i in range(0, len(lines), 30):
            part += 1
            embed = discord.Embed(
                title=f"Personnages possibles ({part}/{parts}) :",
                description="\n".join(lines[i:i + 30]),
                colour=discord.Colour.blue()
            )
            embed.set_author(
                name="Smashthèque",
                icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
            )
            await ctx.send(embed=embed)

    async def do_addcharacters(self, ctx, discord_id, labels):

        # fill characters cache if empty
        await self.fetch_characters_if_needed()

        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        character_ids = player["character_ids"]
        for label in labels.split():
            character = await self.find_character_by_label(ctx, label)
            if character == None:
                return
            character_id = character["id"]
            if character_id in character_ids:
                character_tag = format_character(character)
                await self.raise_message(
                    ctx,
                    f"{character_tag} est déjà indiqué sur ce joueur."
                )
                return
            character_ids.append(character_id)
        await self.update_player(ctx, player["id"], {"character_ids": character_ids})

    async def do_removecharacters(self, ctx, discord_id, labels):

        # fill characters cache if empty
        await self.fetch_characters_if_needed()

        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        character_ids = player["character_ids"]
        for label in labels.split():
            char = await self.find_character_by_label(ctx, label)
            if char == None:
                return
            char_id = char["id"]
            if char_id in character_ids:
                character_ids.remove(char_id)
        if len(character_ids) < 1:
            await self.raise_message(ctx, "Un joueur doit jouer au moins un perso")
            return
        await self.update_player(ctx, player["id"], {"character_ids": character_ids})

    async def do_replacecharacters(self, ctx, discord_id, labels):

        # fill characters cache if empty
        await self.fetch_characters_if_needed()

        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        character_ids = []
        for label in labels.split():
            char = await self.find_character_by_label(ctx, label)
            if char == None:
                return
            character_ids.append(char["id"])
        await self.update_player(ctx, player["id"], {"character_ids": character_ids})

    async def do_chifoumi(self, ctx):
        result = choice(["pile", "face"])
        await ctx.send(result)
        return

    async def maj_team_infos(self, ctx, object_name):

        """will update a team info
        object_name is something like logo, or roster"""
        player = await self.find_member_by_discord_id(ctx.author.id)
        if player is None:
            await yeet(ctx, "Vous n'êtes pas enregistré dans la smashtheque.")
            return
        elif player["administrated_teams"] == []:
            await yeet(ctx, "Vous n'êtes l'admin d'aucune team.")
            return
        attachement = ctx.message.attachments
        if len(attachement) >= 2:
            await yeet(ctx, "Veuillez n'envoyer qu'une seule image.")
            return
        elif len(attachement) == 0:
            await yeet(ctx, f"veuillez envoyer un {object_name} pour la team.")
            return
        team = await self.find_team_by_id(player["administrated_teams"][0]["id"])
        if len(player["administrated_teams"]) > 1:
            embed = discord.Embed(title="Vous âtes administrateur de plusieurs teams. ", description=f"De quelle team faut-il modifier le {object_name} ?")
            for team_entry in player["administrated_teams"]:
                embed.add_field(name=team_entry["short_name"], value=team_entry["name"])
            choice_result = await self.ask_choice(ctx, embed, len(player["administrated_teams"]))
            team = await self.find_team_by_id(player["administrated_teams"][choice_result]["id"])
        embed = discord.Embed(title=f"Vous êtes sur le point de changer le {object_name} de la team {team['name']} pour :")
        embed.set_author(
        name="Smashthèque",
        icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
        )
        embed.set_image(url=ctx.message.attachments[0].url)
        confirmation = await self.ask_confirmation(ctx, embed)
        if not confirmation:
            return
        request_url = f"{self.api_url('teams')}/{team['id']}/"
        reply_body = {
            "team": {
                f"{object_name}_url": ctx.message.attachments[0].url
            }
        }
        async with self._session.patch(request_url, json=reply_body) as response:
            if response.status != 200:
                await generic_error(ctx, f"error in command majlogo : status code {response.status}, response : {response}")
                print(response)
                print(response.text)
                return
            else:
                await self.show_confirmation(ctx, f"Le {object_name} de la team {team['name']} a été mis à jour avec succès.")

    # -------------------------------------------------------------------------
    # COMMANDS
    # -------------------------------------------------------------------------

    @commands.command(usage="<nom>")
    async def creerville(self, ctx, *, name):
        """cette commande va vous permettre d'ajouter une ville dans la Smashthèque.
        \n\nVous devez préciser son nom.
        \n\n\nExemples : \n- creerville Paris\n- creerville Lyon\n"""

        try:
            await self.do_createlocation(ctx, name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<nom>")
    async def creerpays(self, ctx, *, name):
        """cette commande va vous permettre d'ajouter un pays dans la Smashthèque.
        \n\nVous devez préciser son nom.
        \n\n\nExemples : \n- creerpays Belgique\n"""

        try:
            await self.do_createlocation(ctx, name, country=True)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<pseudo> <emojis ou noms de persos> [team] [localisation] [ID Discord]")
    async def creerjoueur(self, ctx, *, arg):
        """cette commande va vous permettre d'ajouter un joueur dans la Smashthèque.
        \n\nVous devez ajouter au minimum le pseudo et les personnages joués (dans l'ordre).
        \n\nVous pouvez aussi ajouter sa team, sa localisation et, s'il possède un compte Discord, son ID pour qu'il puisse modifier lui-même son compte.
        \n\nVous pouvez récupérer l'ID avec les options de developpeur (activez-les dans l'onglet Apparence des paramètres de l'utilisateur, puis faites un clic droit sur l'utilisateur et sélectionnez \"Copier ID\".)
        \n\n\nExemples : \n- creerjoueur Pixel <:Yoshi:737480513744273500> <:Bowser:737480497332224100>\n- creerjoueur Pixel Yoshi Bowser\n- creerjoueur red <:Joker:737480520052637756> LoS Paris 332894758076678144\n"""

        try:
            await self.do_addplayer(ctx, arg)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<pseudo>")
    async def jesuis(self, ctx, *, pseudo):
        """cette commande va vous permettre d'associer votre compte Discord à un joueur de la Smashthèque.
        \n\nVous devez préciser un pseudo.
        \n\n\nExemples : \n- jesuis Pixel\n- jesuis red\n"""

        try:
            await self.do_link(ctx, pseudo, ctx.author.id)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<pseudo> <ID Discord>")
    @commands.admin_or_permissions(administrator=True)
    async def associer(self, ctx, *, arg):
        """cette commande va vous permettre d'associer un compte Discord à un joueur de la Smashthèque.
        \n\nVous devez préciser son pseudo et son ID Discord.
        \n\n\nExemples : \n- associer Pixel 608210202952466464\n- associer red 332894758076678144\n"""

        try:
            args = arg.split()
            pseudo = ' '.join(args[:-1])
            discord_id = args[-1]
            await self.do_link(ctx, pseudo, discord_id)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def jenesuispas(self, ctx):
        """cette commande permet de dissocier votre compte Discord d'un joueur de la Smashthèque.
        \n\n\nExemples : \n- jenesuispas\n"""

        try:
            await self.do_unlink(ctx, ctx.author)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<ID Discord>")
    @commands.admin_or_permissions(administrator=True)
    async def dissocier(self, ctx, *, target_member: discord.Member):
        """cette commande permet de dissocier un compte Discord d'un joueur de la Smashthèque.
        \n\nVous devez préciser son ID Discord.
        \n\n\nExemples : \n- dissocier 608210202952466464\n- dissocier 332894758076678144\n"""

        try:
            await self.do_unlink(ctx, target_member)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<ID Discord>")
    @commands.admin_or_permissions(administrator=True)
    async def quiest(self, ctx, *, target_member: discord.Member):
        try:
            await self.do_showplayer(ctx, target_member)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    async def quisuisje(self, ctx):
        try:
            await self.do_showplayer(ctx, ctx.author)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<nouveau pseudo>")
    async def changerpseudo(self, ctx, *, name):
        try:
            await self.do_editname(ctx, ctx.author.id, name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    async def persos(self, ctx):
        try:
            await self.do_listavailablecharacters(ctx)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<emojis ou noms de persos>")
    async def ajouterpersos(self, ctx, *, emojis):
        try:
            await self.do_addcharacters(ctx, ctx.author.id, emojis)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<emojis ou noms de persos>")
    async def enleverpersos(self, ctx, *, emojis):
        try:
            await self.do_removecharacters(ctx, ctx.author.id, emojis)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<emojis ou noms de persos>")
    async def remplacerpersos(self, ctx, *, emojis):
        try:
            await self.do_replacecharacters(ctx, ctx.author.id, emojis)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<team>")
    async def quitter(self, ctx, *, team_short_name):
        try:
            await self.do_removeteam(ctx, ctx.author.id, team_short_name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<team>")
    async def integrer(self, ctx, *, team_short_name):
        try:
            await self.do_addteam(ctx, ctx.author.id, team_short_name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<localisation>")
    async def enleverlocalisation(self, ctx, *, location_name):
        try:
            await self.do_removelocation(ctx, ctx.author.id, location_name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<localisation>")
    async def ajouterlocalisation(self, ctx, *, location_name):
        try:
            await self.do_addlocation(ctx, ctx.author.id, location_name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<pseudo>")
    async def chercherjoueur(self, ctx, *, name):
        try:
            await self.do_findplayer(ctx, name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    async def pileouface(self, ctx):
        try:
            await self.do_chifoumi(ctx)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    async def majlogo(self, ctx):
        """Utilisez cette commande avec une image pour changer le logo de votre team. \n
        Vous devez être administrateur de la team dont vous voulez changer le logo."""
        try:
            await self.maj_team_infos(ctx, "logo")
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    async def majroster(self, ctx):
        """Utilisez cette commande avec une image pour changer le roster de votre team. \n
        Vous devez être administrateur de la team dont vous voulez changer le roster."""
        try:
            await self.maj_team_infos(ctx, "roster")
        except:
            rollbar.report_exc_info()
            raise
