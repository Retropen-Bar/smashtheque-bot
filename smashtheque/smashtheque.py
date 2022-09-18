from discord.mentions import AllowedMentions
from discord.ext import commands
from discord.commands import permissions
from discord.commands import Option
from discord.enums import SlashCommandOptionType

#from redbot.core.utils.predicates import MessagePredicate

##################### WARNING : COMMENTING OUT THE LINE UP BREAKS THE TOURNAMENT COMMAND ##################

from interactions import st_views

import utils
from utils.responses import respond_or_edit
import discord
import asyncio
import aiohttp
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
from typing import Optional
import inspect

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
        title=f"Erreur dans la commande /{ctx.command.name} :",
        description=erreur,
        colour=discord.Colour.red()
    )
    embed.set_author(
        name="Smashthèque",
        icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
    )
    await ctx.respond(embed=embed)

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
    await ctx.respond(embed=embed)

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

def match_url(v):
    return re.match(r"^((http[s]?|ftp):\/)?\/?([^:\/\s]+)((\/\w+)*\/)([\w\-\.]+[^#?\s]+)(.*)?(#[\w\-]+)?$", v)

def return_false(_):
    """this method is here to always return False on a check, so no one is allowed to run a command, but it can be overwritten later"""
    return False

def is_admin_smashtheque():
    """This is a decorator"""
    with open("config/admins.json", "r") as admins:
        a = json.load(admins)
        print(a)
        admins.close()
        return a
        
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
        rollbar_token = os.environ['ROLLBAR_TOKEN']
        if 'ROLLBAR_ENV' in os.environ and os.environ['ROLLBAR_ENV']:
            rollbar_env = os.environ['ROLLBAR_ENV']
        else:
            rollbar_env = 'production'

        ##rollbar.init(rollbar_token, rollbar_env)

        try:
            self.api_base_url = os.environ['SMASHTHEQUE_API_URL']
            self.api_base_url = "https://www.smashtheque.fr"
            print(f"Smashthèque API base URL set to {self.api_base_url}")
            bearer = os.environ['SMASHTHEQUE_API_TOKEN']
            headers = {
                "Authorization": f"Bearer {bearer}",
                "Content-Type": "application/json",
            }
            self._session = aiohttp.ClientSession(headers=headers)
            self._characters_cache = {}
            self._verbal_characters_names_cache = []
            self._characters_names_cache = {}
            self._locations_cache = {}
            self._teams_cache = {}
            await self.fetch_characters()
        except:
            rollbar.report_exc_info()
            raise
        print("Smashthèque cog loaded")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.loop.create_task(self.initialize())
        self.set_autocomplete_functions()

    def set_autocomplete_functions(self):
        """To autocomplete the st name, we need aiohttp, but by just using a normal autocomplete, we can't access the session
        So, instead, we set here the arguments. 
        When adding a command that uses the session, or anything else in the Cog object, it need to be registered here"""
        self.jesuis.options[0].autocomplete = self.autocomplete_st_name

        self.ajouterperso.options[0].autocomplete = self.autocomplete_characters
        self.enleverperso.options[0].autocomplete = self.autocomplete_characters

        self.integrer.options[0].autocomplete = self.autocomplete_team_name
        self.quitter.options[0].autocomplete = self.autocomplete_current_team_name

        self.chercherjoueur.options[0].autocomplete = self.autocomplete_st_name


        self.creerjoueur.options[1].autocomplete = self.autocomplete_characters
        self.creerjoueur.options[2].autocomplete = self.autocomplete_team_name
        self.creerjoueur.options[2].required = False

        self.associer.options[0].autocomplete = self.autocomplete_st_name

    def cog_unload(self):
        asyncio.create_task(self._session.close())

    def api_url(self, collection):
        return f"{self.api_base_url}/api/v1/{collection}"

    def is_character_name(self, v):
        return normalize_str(v) in self._characters_names_cache

    def is_character(self, v):
        return is_emoji(v) or self.is_character_name(v)

    async def fetch_characters(self):
        async with self._session.get(self.api_url("characters")) as response:
            characters = await response.json()
            # puts values in cache before responding
            for character in characters:
                self._characters_cache[str(character["id"])] = character
                self._verbal_characters_names_cache.append(character["name"])
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

        if self.is_character_name(label) or label.lower() == "pyra" or label.lower() == "mythra":
            character = await self.find_character_by_name(label)
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
    async def find_character_by_name(self, name):
        if name.lower() == "pyra" or name.lower() == "mythra":
            character_id = self._characters_names_cache[normalize_str("pyra/mythra")]
        else:
            character_id = self._characters_names_cache[normalize_str(name)]
        return self._characters_cache[str(character_id)]

    async def find_team_by_name(self, short_name):
        request_url = "{0}?by_name={1}".format(self.api_url("teams"), short_name)
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

    async def find_tournament_by_id(self, tournament_id):
        request_url = f"{self.api_url('recurring_tournaments')}/{tournament_id}"
        async with self._session.get(request_url) as response:
            if response.status == 404:
                return None
            tournament = await response.json()
            return tournament

    async def find_tournament_by_name(self, name):
        request_url = "{0}?by_name={1}".format(self.api_url("teams"), short_name)
        async with self._session.get(request_url) as response:
            teams = await response.json()
            if teams != []:
                # puts values in cache before responding
                for team in teams:
                    self._teams_cache[str(team["id"])] = team
                return teams[0]
            else:
                return None

    async def find_location_by_name(self, name):
        """!!!!!!!!!!!!!!!! probably obsolete !!!!!!!!!!!!!!!!!!!!!!!"""
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

    async def find_players_by_name(self, name):
        """by_name IS NOT IMPLEMENTED YET"""
        raise NotImplementedError
        request_url = "{0}?by_name={1}".format(self.api_url("players"), name)
        async with self._session.get(request_url) as response:
            players = await response.json()
            return players


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

    async def autocomplete_st_name(self, interaction):
        url = self.api_url("players") + "?by_keyword=" + interaction.value + "&order=points_online_all_time_desc"
        async with self._session.get(url) as resp:
            if resp.status == 200:
                r = await resp.json()
                return list(dict.fromkeys([p["name"] for p in r])) # remove any duplicates from list
            else:
                print("SERVER ROOM ON FIRE")
                return None

    async def autocomplete_team_name(self, interaction):
        url = self.api_url("teams") + "?by_keyword=" + interaction.value
        async with self._session.get(url) as resp:
            if resp.status == 200:
                r = await resp.json()
                return list(dict.fromkeys([p["name"] for p in r])) # remove any duplicates from list
            else:
                print("SERVER ROOM ON FIRE")
                return None

    async def autocomplete_current_team_name(self, interaction):
        player = await self.find_player_by_discord_id(interaction.interaction.user.id)
        return list(filter(lambda k: interaction.value in k, player["team_names"]))[:23]

    async def autocomplete_characters(self, interaction):
        #await self.fetch_characters_if_needed()
        return list(filter(lambda k: interaction.value in k, self._verbal_characters_names_cache))[:23]

    async def raise_message(self, ctx, message):
        embed = discord.Embed(title=message)
        embed.set_author(
            name="Smashthèque",
            icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
        )
        await ctx.respond(embed=embed)

    async def raise_not_linked(self, ctx):
        await self.raise_message(ctx, f"Votre compte Discord n'est associé à aucun joueur.\nUtilisez `/jesuis` pour associer votre compte à un joueur.")

    async def show_confirmation(self, ctx, message, link=None):
        embed = discord.Embed(
            title="I guess it's done!",
            description=message,
            colour=discord.Colour.green()
        )
        if link:
            embed.add_field(name=link, value="\u200b")
        await respond_or_edit(ctx, embed=embed)

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
                print(character_id, self._characters_cache)
                personnages.append(format_character(self._characters_cache[str(character_id)]))
        if len(personnages) < 1:
            personnages.append("\u200b")

        player_name = player.name
        if with_index:
            player_name = utils.emojis.NUMBER_EMOJIS[index] + " " + player_name
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
        self.embed_player(embed, player)
        doit = await st_views.ask_confirmation(ctx, embed)
        if doit:
            await self.create_player(ctx, player)

    async def create_player(self, ctx, player):
        payload = {"player": player}
        async with self._session.post(self.api_url("players"), json=payload) as r:
            if r.status == 201:
                # player creation wen fine
                player_name = player["name"]
                await self.show_confirmation(ctx, f"Le joueur {player_name} a été ajouté et sera visible dans les listes sous peu (les commandes sur ce joueur sont tout de même faisables)")
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
                    doit = await st_views.ask_confirmation(ctx, embed)
                    if doit:
                        player["name_confirmation"] = True
                        await self.create_player(ctx, player)
                        
                elif "user_id" in erreur.errors and erreur.errors["user_id"] == ["already_taken"]:
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
                await ctx.respond(embed=embed)
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
                    doit = await st_views.ask_confirmation(ctx, embed)
                    if doit:
                        data["name_confirmation"] = True
                        await self.update_player(ctx, player_id, data)
                elif "discord_user" in erreur.errors and erreur.errors["discord_user"] == ["already_taken"]:
                    await yeet(ctx, "Ce compte Discord est déjà relié à un autre joueur dans la Smashthèque.")
                    return
                else:
                    await generic_error(ctx, erreur)
                    return

    async def complete_bracket_link(self, ctx, tournament):

        await ctx.respond(f"**Lien du bracket pour l'édition du tournoi {tournament['name']} ?** (envoyez stop pour annuler)")
        try:
            message = await self.bot.wait_for('message', timeout=120.0, check=MessagePredicate.same_context(ctx))
        except asyncio.TimeoutError:
            await ctx.respond("commande annulée.")
            return None
        else:
            if message.content.lower() in ["stop", "annuler", "cancel"]:
                await ctx.respond("commande annulée.")
                return None
            return message.content

    async def complete_tournament_graph(self, ctx):
        """no idea how to check if the tournament has a graph"""
        await ctx.respond("Si votre tournois possède un graph, veuillez réutiliser la même commande avec le lien du tournois comme argument, et le graph comme attachement.")
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

    async def do_addplayer(self, ctx, pseudo, perso, team, discord_id):

        # fill characters cache if empty
        await self.fetch_characters_if_needed()

        # stages:
        # 0: pseudo
        # 1: characters
        # 2: team
        # --3: location-- removed
        # 3: discord ID

        current_stage = 0
        char = await self.find_character_by_name(perso)
        # init de la réponse
        response = {
            "name": pseudo,
            "character_ids": char,
            "creator_discord_id": "",
            "team_ids": []
        }

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

    async def do_link(self, ctx:discord.ApplicationContext, pseudo, discord_id):
        player = await self.find_player_by_discord_id(discord_id)
        if player != None:
            embed = discord.Embed(title="Un joueur est déjà associé à ce compte Discord. Contactez un admin pour dissocier ce compte Discord de ce joueur.")
            self.embed_player(embed, player)
            await ctx.respond(embed=embed)
            return

        players = await self.find_players_by_name(pseudo)

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
            doit = await st_views.ask_confirmation(ctx, embed)
            if not doit:
                return
            if player["discord_id"] != None:
                await self.raise_message(ctx, "Il semblerait que ce joueur soit déjà associé à un compte Discord")
                return
            await self.update_player(ctx, player["id"], {"discord_id": str(discord_id)})
            discord_user = format_discord_user(discord_id)
            await self.show_confirmation(ctx, f"Le compte Discord {discord_user} est maintenant associé au joueur {pseudo}.", link=f"{self.api_base_url}/players/{player['id']}")
            return

        # multiple players found: ask which one
        embed = discord.Embed(
            title="Plusieurs joueurs ont ce pseudo.\nChoisissez le bon joueur dans la liste ci-dessous grâce aux réactions",
            colour=discord.Colour.blue()
        )
        self.embed_players(embed, players, with_index=True)
        choice = await st_views.ask_choice(ctx, embed, players)
        if choice == None:
            return
        player = players[choice]
        if player["discord_id"] != None:
            await self.raise_message(ctx, "Il semblerait que ce joueur soit déjà associé à un compte Discord")
            return
        await self.update_player(ctx, player["id"], {"discord_id": str(discord_id)})
        discord_user = format_discord_user(discord_id)
        await self.show_confirmation(ctx, f"Le compte Discord {discord_user} est maintenant associé au joueur {pseudo}.", link=f"{self.api_base_url}/players/{player['id']}")

    async def do_unlink(self, ctx, target_member):
        discord_id = target_member.id
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        embed = discord.Embed(title="Un joueur est associé à ce compte discord. Voulez vous le dissocier ?")
        embed.set_footer(text="Réagissez avec ✅ pour confirmer et dissocier ce compte du joueur, ou\nréagissez avec ❎ pour annuler.")
        self.embed_player(embed, player)
        doit = await st_views.ask_confirmation(ctx, embed)
        if not doit:
            return
        await self.update_player(ctx, player["id"], {"discord_id": None})
        player_name = player["name"]
        discord_user = format_discord_user(discord_id)
        await self.show_confirmation(ctx, f"Le compte Discord {discord_user} a été dissocié du joueur {player_name}.", link=f"{self.api_base_url}/players/{player['id']}")

    async def do_showplayer(self, ctx: discord.ApplicationContext, target_member, ephemeral = False):
        discord_id = target_member.id
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        embed = discord.Embed(
            title="Ce compte Discord est associé au joueur suivant :",
            colour=discord.Colour.green(),
            url=f"{self.api_base_url}/players/{player['id']}"
        )
        self.embed_player(embed, player)
        embed.set_footer(text=f"Pour {ctx.author}", icon_url=ctx.author.display_avatar.url)
        if ephemeral:
            view = st_views.makeEphemeralPublic()
            await ctx.respond(embed=embed, ephemeral = True, view = view)
            return
        await ctx.respond(embed=embed, ephemeral = False)

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
        await ctx.respond(embed=embed)
        return

    async def do_editname(self, ctx, discord_id, new_name):
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        await self.update_player(ctx, player["id"], {"name": new_name})

    async def do_removeteam(self, ctx, discord_id, team_name):
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        team_ids = player["team_ids"]
        team = await self.find_team_by_name(team_name)
        if team == None:
            await self.raise_message(
                ctx,
                f"Nous n'avons pas réussi à trouver l'équipe {team_name}.\nVous pouvez demander à un administrateur de la créer."
            )
            return
        team_id = team["id"]
        if team_id in team_ids:
            team_ids.remove(team_id)
        await self.update_player(ctx, player["id"], {"team_ids": team_ids})

    async def do_addteam(self, ctx, discord_id, team_name):
        player = await self.find_player_by_discord_id(discord_id)
        if player == None:
            await self.raise_not_linked(ctx)
            return
        team_ids = player["team_ids"]
        team = await self.find_team_by_name(team_name)
        if team == None:
            await self.raise_message(
                ctx,
                f"Nous n'avons pas réussi à trouver l'équipe {team_name}.\nVous pouvez demander à un administrateur de la créer."
            )
            return
        team_id = team["id"]
        if team_id in team_ids:
            await self.raise_message(
                ctx,
                f"Ce joueur est déjà membre de l'équipe {team_name}."
            )
            return
        team_ids.append(team_id)
        await self.update_player(ctx, player["id"], {"team_ids": team_ids})

    async def do_force_add_team(self, ctx, player_id, team_short_name, remove):
        player = await self.find_player_by_id(player_id)
        if player == None:
            await yeet(ctx, "Ce joueur n'existe pas !")
            return
        team_ids = player["team_ids"]
        team = await self.find_team_by_short_name(team_short_name)
        if team == None:
            await self.raise_message(
                ctx,
                f"Cette team n'existe pas !"
            )
            return
        team_id = team["id"]
        if remove == False:
            if team_id in team_ids:
                await self.raise_message(
                    ctx,
                    f"Ce joueur est déjà membre de l'équipe {team_short_name}."
                )
                return
            team_ids.append(team_id)
            final_message = f"La team {team_short_name} a été ajouté au joueur."
        else:
            if team_ids == []:
                await yeet(ctx, "Ce joueur n'a pas de teams !")
                return
            if team_id in team_ids:
                team_ids.remove(team_id)
            else:
                await yeet(ctx, "Ce joueur n'est pas membre de cette team !")
                return
            final_message = f"La team {team_short_name} a été supprimé du joueur."

        await self.update_player(ctx, player["id"], {"team_ids": team_ids})
        await self.show_confirmation(ctx, final_message, link=f"{self.api_base_url}/players/{player_id}")

    async def do_listavailablecharacters(self, ctx):
        """MARKED FOR REMOVAL"""

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
        message_list = []
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
            message_list.append(await ctx.respond(embed=embed))

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
        await ctx.respond(result)
        return

    async def maj_team_infos(self, ctx, attachement: discord.Attachment, object_name):

        """will update a team info
        object_name is something like logo, or roster"""
        player = await self.find_member_by_discord_id(ctx.author.id)
        if player is None:
            await yeet(ctx, "Vous n'êtes pas enregistré dans la smashtheque.")
            return
        elif player["administrated_teams"] == []:
            await yeet(ctx, "Vous n'êtes l'admin d'aucune team.")
            return

        team = await self.find_team_by_id(player["administrated_teams"][0]["id"])
        if len(player["administrated_teams"]) > 1:
            embed = discord.Embed(title="Vous âtes administrateur de plusieurs teams. ", description=f"De quelle team faut-il modifier le {object_name} ?")
            for team_entry in player["administrated_teams"]:
                embed.add_field(name=team_entry["short_name"], value=team_entry["name"])
            choice_result = await st_views.ask_choice(ctx, embed, player["administrated_teams"])
            if choice_result == None:
                return
            team = await self.find_team_by_id(player["administrated_teams"][choice_result]["id"])
        embed = discord.Embed(title=f"Vous êtes sur le point de changer le {object_name} de la team {team['name']} pour :")
        embed.set_author(
        name="Smashthèque",
        icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
        )
        embed.set_image(url=attachement.url)
        confirmation = await st_views.ask_confirmation(ctx, embed)
        if not confirmation:
            return
        request_url = f"{self.api_url('teams')}/{team['id']}/"
        reply_body = {
            "team": {
                f"{object_name}_url": attachement.url
            }
        }
        async with self._session.patch(request_url, json=reply_body) as response:
            if response.status != 200:
                await generic_error(ctx, f"error in command majlogo : status code {response.status}, response : {response}")
                print(response)
                print(response.text)
                return
            else:
                await self.show_confirmation(ctx, f"Le {object_name} de la team {team['name']} a été mis à jour avec succès.", link = f"{self.api_base_url}/teams/{team['id']}")

    async def do_addedition(self, ctx, bracket):
        """MARKED FOR REMOVAL. Is deprecated, insertedition will be used instead"""
        #generic checks
        player = await self.find_member_by_discord_id(ctx.author.id)
        if player is None:
            await yeet(ctx, "Vous n'êtes pas enregistré dans la smashtheque.")
            return
        elif player["administrated_recurring_tournaments"] == []:
            await yeet(ctx, "Vous n'êtes l'admin d'aucun tournoi.")
            return

        #selecting the right tournament
        if len(player["administrated_recurring_tournaments"]) > 1:
            idx = 1
            admin_recuring_tournaments = player["administrated_recurring_tournaments"].copy()
            descript = ">>> " + admin_recuring_tournaments[0]["name"]
            admin_recuring_tournaments.pop(0)
            for tournament_entry in admin_recuring_tournaments:
                descript += f"\n\n" + tournament_entry["name"]
                idx += 1
            embed = discord.Embed(title="Vous êtes administrateur de plusieurs tournois. Quel est le tournoi concerné ?", description=descript, color=0x2f2136)
            
            choice = await st_views.ask_choice(ctx, embed, player["administrated_recurring_tournaments"])
            if choice == None:
                return
            tournament = await self.find_tournament_by_id(player["administrated_recurring_tournaments"][choice]["id"])

        else:
            tournament = await self.find_tournament_by_id(player["administrated_recurring_tournaments"][0]["id"])

        #completing the bracket link
        if not bracket:
            bracket = await self.complete_bracket_link(ctx, tournament)
            if not bracket:
                return

        """
        #parse the tournament link/id
        regex = match_url(bracket)

        if not regex or regex[3] not in ["challonge.com", "smash.gg", "https://challonge.com", "https://smash.gg"]:
            await yeet(ctx, "Veuillez envoyer l'url d'un tournois challonge ou smash.gg valide.")
            return
        """
        attachement = ctx.message.attachments
        if len(attachement) >= 2:
            await yeet(ctx, "Veuillez n'envoyer qu'une seule image.")
            return
        #if no attachment in the original command, asking for it
        elif len(attachement) == 0:
            await self.complete_tournament_graph(ctx)

        embed = discord.Embed(title=f"Vous êtes sur le point d'ajouter une édition au tournois {tournament['name']}", description="Confirmer ?")
        embed.set_author(
            name="Smashthèque",
            icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
        )
        embed.set_footer(text="Vous pouvez ajouter l'url du tournois, la commande ainsi que le graph du tournois dans un seul")
        if not await st_views.ask_confirmation(ctx, embed):
            await ctx.respond("Commande annulée.")
            return
        tournament_response = {
            "tournament_event": {
                "recurring_tournament_id": tournament["id"],
                "bracket_url": bracket
            }
        }
        if len(attachement) == 1:
            tournament_response["tournament_event"]["graph_url"] = attachement[0].url
        request_url = self.api_url("tournament_events")
        async with self._session.post(request_url, json=tournament_response) as r:
            if r.status == 201:
                await self.show_confirmation(ctx, f"Une édition du tournois {tournament['name']} a été crée avec succès.", link=f"{self.api_base_url}/tournament_events/{tournament['id']}")
            elif r.status == 200:
                await self.show_confirmation(ctx, f"Une édition du tournois {tournament['name']} a été modifié avec succès.", link=f"{self.api_base_url}/tournament_events/{tournament['id']}")
            elif r.status == 422:
                await yeet(ctx, "Ce tournoi est déjà enregistré dans la Smashthèque.")
                return

    async def do_insertedition(self, ctx:discord.ApplicationContext, series_id, attachement, bracket):
        embed_title_message = "Vous êtes sur le point d'ajouter une édition" # Will be overriden if series id is present
        if series_id:
            tournament = await self.find_tournament_by_id(series_id)
            print(tournament)
            if not tournament:
                await yeet(ctx, "Cette ID ne correspond à aucun tournoi.")
                return
            embed_title_message = f"Vous êtes sur le point d'ajouter une édition au tournois {tournament['name']}"
        else:
            player = await self.find_member_by_discord_id(ctx.author.id)
            if player is None:
                await yeet(ctx, "Vous n'êtes pas enregistré dans la smashtheque.")
                return
            elif player["administrated_recurring_tournaments"] == []:
                await yeet(ctx, "Vous n'êtes administrateur d'aucun tournoi.\nPour ajouter une édition d'un tournoi dont vous n'êtes pas l'administrateur, utilisez l'ID de la série.")
                return

            #selecting the right tournament
            if len(player["administrated_recurring_tournaments"]) > 1:
                idx = 1
                admin_recuring_tournaments = player["administrated_recurring_tournaments"].copy()
                descript = ">>> " + admin_recuring_tournaments[0]["name"]
                admin_recuring_tournaments.pop(0)
                for tournament_entry in admin_recuring_tournaments:
                    descript += f"\n\n" + tournament_entry["name"]
                    idx += 1
                embed = discord.Embed(title="Vous êtes administrateur de plusieurs tournois. Quel est le tournoi concerné ?", description=descript, color=0x2f2136)
                
                choice = await st_views.ask_choice(ctx, embed, player["administrated_recurring_tournaments"])
                if choice == None:
                    return
                tournament = await self.find_tournament_by_id(player["administrated_recurring_tournaments"][choice]["id"])

            else:
                tournament = await self.find_tournament_by_id(player["administrated_recurring_tournaments"][0]["id"])

        
        embed = discord.Embed(title=embed_title_message, description="Confirmer ?")
        embed.set_author(
            name="Smashthèque",
            icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
        )
        tournament_response = {
            "tournament_event": {
                "bracket_url": bracket,
                "recurring_tournament_id": tournament["id"]
            }
        }
        if series_id: # add id to reply if present
            tournament_response["recurring_tournament_id"] = series_id

        print(attachement)
        if attachement:
            tournament_response["tournament_event"]["graph_url"] = attachement.url
        request_url = self.api_url("tournament_events")
        async with self._session.post(request_url, json=tournament_response) as r:

            response = await r.json()
            if r.status == 201:
                await self.show_confirmation(ctx, f"Une édition a été crée avec succès.", link=f"{self.api_base_url}/tournament_events/{response['id']}")
            elif r.status == 200:
                await self.show_confirmation(ctx, f"Une édition a été modifié avec succès.", link=f"{self.api_base_url}/tournament_events/{response['id']}")
            elif r.status == 422:
                await yeet(ctx, "Ce tournoi est déjà enregistré dans la Smashthèque.")
                return
            else:
                await generic_error(ctx)

    async def do_add_admin_smashtheque(self, ctx, member):
        with open("config/admins.json", "w") as admins:
            admins_json = json.load(admins)
            print(admins_json)
            admins_json.append(member.id)
            json.dump(admins_json, admins)
        await ctx.respond("Done !")

    async def do_add_self_twitter_profile_connection(self, ctx, link):
        player = await self.find_player_by_discord_id(ctx.author.id)
        if player is None:
            await yeet(ctx, "Vous n'êtes pas enregistré dans la smashtheque.")
            return
        request = {"twitter_url": link}
        url = self.api_url("users") + "/" + str(player["user_id"])
        async with self._session.patch(url, json=request) as r:
            if r.status == 200:
                await self.show_confirmation(ctx, "Votre profil a été mis à jour avec succès !", link=f"{self.api_base_url}/players/{player['id']}")
            else:
                print(r)
                print(await r.json())
                await generic_error(ctx, r)

    async def do_add_twitter_profile_connection(self, ctx, link, discord_id):
        """adds a profile connection for someone else"""
        player = await self.find_player_by_discord_id(discord_id)
        if player is None:
            await yeet(ctx, "Ce joueur n'est pas enregistré dans la smashthèque.")
            return
        request = {"twitter_url": link}
        url = self.api_url("users") + "/" +str(player["user_id"])
        async with self._session.patch(url, json=request) as r:
            if r.status == 200:
                await self.show_confirmation(ctx, "Ce profil a été mis à jour avec succès !", link=f"{self.api_base_url}/players/{player['id']}")
            else:
                await generic_error(ctx, r)

    async def do_add_self_smashgg_profile_connection(self, ctx, link):
        player = await self.find_player_by_discord_id(ctx.author.id)
        if player is None:
            await yeet(ctx, "Vous n'êtes pas enregistré dans la smashtheque.")
            return
        request = {"player":{"smashgg_url": link}}
        url = self.api_url("players") + "/" + str(player["id"])
        async with self._session.patch(url, json=request) as r:
            if r.status == 200:
                await self.show_confirmation(ctx, "Votre profil a été mis à jour avec succès !", link=f"{self.api_base_url}/players/{player['id']}")
            else:
                print(r)
                print(await r.json())
                await generic_error(ctx, r)

    async def do_add_smashgg_profile_connection(self, ctx, link, discord_id):
        """adds a profile connection for someone else"""
        player = await self.find_player_by_discord_id(discord_id)
        if player is None:
            await yeet(ctx, "Ce joueur n'est pas enregistré dans la smashthèque.")
            return
        request = {"player":{"smashgg_url": link}}
        url = self.api_url("players") + "/" +str(player["id"])
        async with self._session.patch(url, json=request) as r:
            if r.status == 200:
                await self.show_confirmation(ctx, "Ce profil a été mis à jour avec succès !", link=f"{self.api_base_url}/players/{player['id']}")
            else:
                await generic_error(ctx, r)

    # -------------------------------------------------------------------------
    # COMMANDS
    # -------------------------------------------------------------------------

    @commands.slash_command()
    async def creerville(self, ctx, name):
        """cette commande va vous permettre d'ajouter une ville dans la Smashthèque.
        \n\nVous devez préciser son nom.
        \n\n\nExemples : \n- creerville Paris\n- creerville Lyon\n"""

        try:
            await self.do_createlocation(ctx, name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    async def creerpays(self, ctx, name):
        """cette commande va vous permettre d'ajouter un pays dans la Smashthèque.
        \n\nVous devez préciser son nom.
        \n\n\nExemples : \n- creerpays Belgique\n"""

        try:
            await self.do_createlocation(ctx, name, country=True)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    @discord.option("pseudo", str)
    @discord.option("perso", str)
    @discord.option("team", str, required=False)
    @discord.option("id_discord", str, required=False)
    async def creerjoueur(self, ctx, pseudo, perso, team, id_discord):
        """cette commande va vous permettre d'ajouter un joueur dans la Smashthèque."""

        try:
            await self.do_addplayer(ctx, pseudo, perso, team, id_discord)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    @discord.option("pseudo", str) # name autocomplete registered during init
    async def jesuis(self, ctx,  pseudo):
        """cette commande va vous permettre d'associer votre compte Discord à un joueur de la Smashthèque.
        \n\nVous devez préciser un pseudo.
        \n\n\nExemples : \n- jesuis Pixel\n- jesuis red\n"""

        try:
            await self.do_link(ctx, pseudo, ctx.author.id)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command(user_ids=is_admin_smashtheque())
    @discord.option("pseudo", str) #autocomplete
    @discord.option("discord_id", str) 
    async def associer(self, ctx, pseudo, discord_id):
        """cette commande va vous permettre d'associer un compte Discord à un joueur de la Smashthèque.
        \n\nVous devez préciser son pseudo et son ID Discord.
        \n\n\nExemples : \n- associer Pixel 608210202952466464\n- associer red 332894758076678144\n"""

        try:
            await self.do_link(ctx, pseudo, discord_id)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    async def jenesuispas(self, ctx):
        """cette commande permet de dissocier votre compte Discord d'un joueur de la Smashthèque."""

        try:
            await self.do_unlink(ctx, ctx.author)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<ID Discord>")
    @commands.check(is_admin_smashtheque)
    async def dissocier(self, ctx, *, target_member: discord.Member):
        """cette commande permet de dissocier un compte Discord d'un joueur de la Smashthèque."""

        try:
            await self.do_unlink(ctx, target_member)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<ID Discord>")
    @commands.check(is_admin_smashtheque)
    async def quiest(self, ctx, *, target_member: discord.Member):
        """Cette commande vous permet de savoir qui est le joueur de la Smashthèque associé à un compte Discord."""
        try:
            await self.do_showplayer(ctx, target_member, False)
        except:
            rollbar.report_exc_info()
            raise

    @commands.user_command(name="qui est", )
    async def quiest(self, ctx, target_member: discord.Member):

        try:
            await self.do_showplayer(ctx, target_member, True)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    async def quisuisje(self, ctx):
        """Permet de savoir qui est le joueur de la Smashthèque associé à votre compte Discord."""
        try:
            await self.do_showplayer(ctx, ctx.author)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    async def changerpseudo(self, ctx, name:str):
        try:
            await self.do_editname(ctx, ctx.author.id, name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    @discord.option("persos", str) # name autocomplete registered during init
    async def ajouterperso(self, ctx, persos):
        try:
            await self.do_addcharacters(ctx, ctx.author.id, persos)
        except:
            rollbar.report_exc_info()
            raise
    
    @commands.slash_command()
    @discord.option("persos", str) # name autocomplete registered during init
    async def enleverperso(self, ctx, *, persos):
        try:
            await self.do_removecharacters(ctx, ctx.author.id, persos)
        except:
            rollbar.report_exc_info()
            raise
    """
    It is not possible to take an unknown number of arguments, so we have to use a string.
    @commands.command(usage="<emojis ou noms de persos>")
    async def remplacerpersos(self, ctx, *, emojis):
        try:
            await self.do_replacecharacters(ctx, ctx.author.id, emojis)
        except:
            rollbar.report_exc_info()
            raise"""

    @commands.slash_command()
    @discord.option("equipe", str) # name autocomplete registered during init
    async def quitter(self, ctx, equipe):
        try:
            await self.do_removeteam(ctx, ctx.author.id, equipe)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    @discord.option("equipe", str) # name autocomplete registered during init
    async def integrer(self, ctx, equipe):
        try:
            await self.do_addteam(ctx, ctx.author.id, equipe)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    @discord.option("nom", str) # name autocomplete registered during init
    async def chercherjoueur(self, ctx, nom):
        try:
            await self.do_findplayer(ctx, nom)
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

    @commands.slash_command()
    async def majlogo(self, ctx, logo: Option(SlashCommandOptionType.attachment, "Logo de votre équipe")):
        """Utilisez cette commande avec une image pour changer le logo de votre team. \n
        Vous devez être administrateur de la team dont vous voulez changer le logo."""
        try:
            await self.maj_team_infos(ctx, logo, "logo")
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    async def majroster(self, ctx, logo: Option(SlashCommandOptionType.attachment, "Roaster de votre équipe")):
        """Utilisez cette commande avec une image pour changer le roster de votre team. \n
        Vous devez être administrateur de la team dont vous voulez changer le roster."""
        try:
            await self.maj_team_infos(ctx, logo, "roster")
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    async def ajouttournoi(self, ctx, 
                            bracket: Option(
                                SlashCommandOptionType.string, "Lien du bracket"), 
                            graph: Option(
                                SlashCommandOptionType.attachment, "Graph du tournoi", required=False),
                            serie: Option(
                                SlashCommandOptionType.integer, "ID de la série", required=False)
                                ):
        """
        Cette commande permet aux joueurs d'ajouter une édition dans la smashthèque.
        """
        try:
            await self.do_insertedition(ctx, serie, graph, bracket)
        except:
            rollbar.report_exc_info()
            raise

    @commands.is_owner()
    @commands.command()
    async def addadmin(self, ctx, member:discord.Member):
        try:
            await self.do_add_admin_smashtheque(ctx, member)
        except:
            rollbar.report_exc_info()
            raise

    @commands.check(is_admin_smashtheque)
    @commands.command()
    async def forceteam(self, ctx, smashtheque_user_id, short_team_name, remove:bool = False):
        try:
            await self.do_force_add_team(ctx, smashtheque_user_id, short_team_name, remove)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    async def ajoutertwitter(self, ctx, lien: Option(
                                SlashCommandOptionType.string, "Lien de votre compte twitter")):
        try:
            await self.do_add_self_twitter_profile_connection(ctx, lien)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command(user_ids=is_admin_smashtheque())
    async def inserertwitter(self, ctx, lien: Option(
                                SlashCommandOptionType.string, "Lien de votre compte twitter"), 
                                discord_id: Option(
                                    SlashCommandOptionType.string, "ID discord du joueur")
                                ):
        try:
            await self.do_add_twitter_profile_connection(ctx, lien, "twitter_url", discord_id)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command()
    async def ajoutersmashgg(self, ctx, lien: Option(
                                SlashCommandOptionType.string, "Lien de votre compte smash.gg")):
        try:
            await self.do_add_self_smashgg_profile_connection(ctx, lien)
        except:
            rollbar.report_exc_info()
            raise

    @commands.slash_command(user_ids=is_admin_smashtheque())
    async def inserersmashgg(self, ctx, lien: Option(
                                SlashCommandOptionType.string, "Lien du compte smash.gg"), 
                                discord_id: Option(
                                    SlashCommandOptionType.string, "ID discord du joueur")
                                ):
        try:
            await self.do_add_smashgg_profile_connection(ctx, lien, discord_id)
        except:
            rollbar.report_exc_info()
            raise

