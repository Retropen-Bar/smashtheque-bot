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
import rollbar
import os
import sys
from collections.abc import Mapping
from collections import UserDict

async def yeet(ctx, erreur):
    """lever des erreurs"""
    embed = discord.Embed(
        title=f"Erreur dans la commande {ctx.command} :",
        description=erreur,
        colour=discord.Colour(0xD0021B),
    )
    embed.set_author(
        name="smashthèque ",
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
        colour=discord.Colour(0xD0021B),
    )
    embed.set_author(
        name="smashthèque ",
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


def format_emojis(id_list):
    """transformer des émoji id en émojis discord"""
    end = ""
    print(id_list)
    for i in id_list:
        print(i)
        end = end + f"<:placeholder:{i}>"
    return end


def is_discord_id(v):
    return v.isdigit() and len(str(v)) == 18

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
            self._cities_cache = {}
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


    async def fetch_characters(self):
        print('fetch_characters')
        async with self._session.get(self.api_url("characters")) as response:
            characters = await response.json()
            # puts values in cache before responding
            for character in characters:
                self._characters_cache[str(character["id"])] = character
            # respond
            return characters

    # this only works if self.fetch_characters() has been called at least once
    async def find_character_by_emoji_tag(self, ctx, emoji):
        if len(self._characters_cache) < 1:
            print(f"self._characters_cache = {self._characters_cache}")
            raise CharactersCacheNotFetched
        emoji_id = re.search(r"[0-9]+", emoji).group()
        for character_id in self._characters_cache:
            character = self._characters_cache[str(character_id)]
            if character["emoji"] == emoji_id:
                return character
        await yeet(
            ctx,
            f"Emoji {emoji} non reconnu : veuillez utiliser les émojis de personnages de ce serveur."
        )
        return None

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

    async def find_city_by_name(self, name):
        request_url = "{0}?by_name_like={1}".format(self.api_url("cities"), name)
        async with self._session.get(request_url) as response:
            cities = await response.json()
            if cities != []:
                # puts values in cache before responding
                for city in cities:
                    self._cities_cache[str(city["id"])] = city
                return cities[0]
            else:
                return None

    def embed_players(self, embed, players, with_index=False):
        idx = 0
        for player in players:
            if idx > 0:
                embed.add_field(name="\u200b", value="\u200b", inline=False)
            self.embed_player(embed, player, with_index=with_index, index=idx+1)
            idx += 1

    def embed_player(self, embed, _player, with_index=False, index=0):
        print(f"embed player {_player}")
        player = Map(_player)

        alts_emojis = []
        if "characters" in _player:
            for character in player.characters:
                alts_emojis.append(character["emoji"])
        elif "character_ids" in _player:
            for character_id in player.character_ids:
                alts_emojis.append(self._characters_cache[str(character_id)]["emoji"])
        personnages = format_emojis(alts_emojis)

        player_name = player.name
        if with_index:
            player_name = ReactionPredicate.NUMBER_EMOJIS[index] + " " + player_name
        embed.add_field(name=player_name, value=personnages, inline=True)

        team_name = None
        if "team" in _player and player.team != None:
            team_name = player.team["name"]
        elif "team_id" in _player and player.team_id != None:
            team_name = self._teams_cache[str(player.team_id)]["name"]
        if team_name != None:
            embed.add_field(name="Team", value=team_name, inline=True)

        city_name = None
        if "city" in _player and player.city != None:
            city_name = player.city["name"]
        elif "city_id" in _player and player.city_id != None:
            city_name = self._cities_cache[str(player.city_id)]["name"]
        if city_name != None:
            embed.add_field(name="Ville", value=city_name, inline=True)

    async def confirm_create_player(self, ctx, player):
        embed = discord.Embed(
            title="Vous allez créer le joueur suivant :",
            colour=discord.Colour(0xA54C4C),
        )
        embed.set_footer(text="Réagissez avec ✅ pour confirmer et créer ce joueur, ou réagissez avec ❎ pour annuler.")
        self.embed_player(embed, player)
        temp_message = await ctx.send(embed=embed)
        pred = ReactionPredicate.yes_or_no(temp_message, ctx.author)
        start_adding_reactions(temp_message, ReactionPredicate.YES_OR_NO_EMOJIS)
        try:
            await self.bot.wait_for(
                "reaction_add", timeout=60.0, check=pred
            )
        except asyncio.TimeoutError:
            await ctx.send("Commande annulée")
        if pred.result is True:
            await temp_message.delete()
            await self.create_player(ctx, player)
        else:
            await ctx.send("Commande annulée")
            await temp_message.delete()
            return


    async def create_player(self, ctx, player):
        print(f"create player {player}")
        payload = {"player": player}
        async with self._session.post(self.api_url("players"), json=payload) as r:
            if r.status == 422:
                result = await r.json()
                erreur = Map(result)
                print(erreur.errors["name"])
                if erreur.errors["name"] == "already_known":
                    alts = []
                    for i in erreur.errors["existing_ids"]:
                        player_url = self.api_url("players")
                        player_url += "/"
                        player_url += str(i)
                        async with self._session.get(player_url) as r:
                            print(await r.json())
                            result = await r.json()
                            alts.append(result)
                            print(alts)
                    embed = discord.Embed(
                        title="Un ou plusieurs joueurs possèdent le même pseudo que le joueur que vous souhaitez ajouter.",
                        colour=discord.Colour(0xA54C4C),
                    )
                    embed.set_footer(text="Réagissez avec ✅ pour confirmer et créer un nouveau joueur, ou\nréagissez avec ❎ pour annuler.")
                    self.embed_players(embed, alts)
                    temp_message = await ctx.send(embed=embed)
                    pred = ReactionPredicate.yes_or_no(temp_message, ctx.author)
                    start_adding_reactions(
                        temp_message, ReactionPredicate.YES_OR_NO_EMOJIS
                    )
                    try:
                        await self.bot.wait_for(
                            "reaction_add", timeout=60.0, check=pred
                        )
                    except asyncio.TimeoutError:
                        await ctx.send("Commande annulée")
                    if pred.result is True:
                        await temp_message.delete()
                        player["name_confirmation"] = True
                        await self.create_player(ctx, player)
                    else:
                        await ctx.send("Commande annulée")
                        await temp_message.delete()
                        return
                else:
                    await generic_error(ctx, erreur)
                    return

        # player creation wen fine
        embed = discord.Embed(
            title=f"\"I guess it's done!\".\nLe joueur a été ajouté à la base de données.",
            colour=discord.Colour(0xA54C4C),
        )
        await ctx.send(embed=embed)

    async def do_addcity(self, ctx, name):
        print(f"create city {name}")
        payload = {"name": name}
        async with self._session.post(self.api_url("cities"), json=payload) as r:
            if r.status == 201:
                # city creation went fine
                embed = discord.Embed(
                    title=f"\"I guess it's done!\".\nLa ville a été ajoutée à la base de données.",
                    colour=discord.Colour(0xA54C4C),
                )
                await ctx.send(embed=embed)
                return

            if r.status == 422:
                result = await r.json()
                erreur = Map(result)
                print(erreur.errors["name"])
                if erreur.errors["name"] == ["not_unique"]:
                    await yeet(ctx, "Cette ville existe déjà dans la Smashthèque.")
                    return

            # something went wrong but we don't know what
            await generic_error(ctx, r)
            return

    async def do_addplayer(self, ctx, arg):

        # fetch characters once
        await self.fetch_characters()

        # stages:
        # 0: pseudo
        # 1: characters
        # 2: team
        # 3: city
        # 4: discord ID

        current_stage = 0

        # init de la réponse
        response = {"name": "", "character_ids": [], "creator_discord_id": ""}

        # process each argument between spaces
        # [name piece] [name piece] [emoji] [emoji] [team] [city] [discord ID]
        arguments = arg.split()

        for argu in arguments:
            print(f"current_stage={current_stage} argu={argu}")

            if current_stage == 0:
                print('stage 0')
                # at this stage, the next argument could be a name piece
                # ... [name piece] [emoji] [emoji] [team] [city] [discord ID]

                if is_emoji(argu):
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
                # ... [emoji] [emoji] [team] [city] [discord ID]

                if not is_emoji(argu):
                    # we are actually done with the emojis, so go to stage 2
                    current_stage = 2
                    # do not 'continue' here because we stil want to process @argu
                else:
                    # more emojis to parse
                    character = await self.find_character_by_emoji_tag(ctx, argu)
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
                # ... [team] [city] [discord ID]

                if is_discord_id(argu):
                    response["discord_id"] = str(argu)
                    break

                team = await self.find_team_by_short_name(argu)
                if team != None:
                    response["team_id"] = team["id"]
                    current_stage = 3
                    continue

                # nope, not a team, try next stage
                current_stage = 3

            # do not use elif here because we want the previous section to be able to go here
            # without restarting the loop
            if current_stage == 3:
                print('stage 3')
                # at this stage, the next argument could be a city
                # ... [city] [discord ID]

                if is_discord_id(argu):
                    response["discord_id"] = str(argu)
                    break

                city = await self.find_city_by_name(argu)
                if city != None:
                    response["city_id"] = city["id"]
                    current_stage = 4
                    continue

                # nope, not a city
                # so we have a problem here
                # because argu is neither a city nor a Discord ID
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
                if "city_id" in response and response["city_id"] != None:
                    # we have a city, so we are pretty sure argu was supposed to be a Discord ID
                    await yeet(
                        ctx,
                        f"Veuillez entrer un ID Discord correct pour le joueur à ajouter : {argu} n'en est pas un.\nPour avoir l'ID d'un utilisateur, activez simplement les options de développeur dans l'onglet apparence de discord, puis faites un clic droit sur l'utilisateur > copier l'identifiant."
                    )
                    return
                elif "team_id" in response and response["team_id"] != None:
                    # we have a team, so argu could be for a city or a Discord ID
                    await yeet(
                        ctx,
                        f"Nous n'avons pas réussi à reconnaître {argu}.\nS'il s'agit d'une ville, vous pouvez la créer avec !addcity.\nS'il s'agit d'un ID Discord, il n'est pas correct\nPour avoir l'ID d'un utilisateur, activez simplement les options de développeur dans l'onglet apparence de discord, puis faites un clic droit sur l'utilisateur > copier l'identifiant."
                    )
                    return
                else:
                    # we have no team and no city: argu could be for a team, a city or a Discord ID
                    await yeet(
                        ctx,
                        f"Nous n'avons pas réussi à reconnaître {argu}.\nS'il s'agit d'une équipe, vous devez demander à un administrateur de la créer.\nS'il s'agit d'une ville, vous pouvez la créer avec !addcity.\nS'il s'agit d'un ID Discord, il n'est pas correct\nPour avoir l'ID d'un utilisateur, activez simplement les options de développeur dans l'onglet apparence de discord, puis faites un clic droit sur l'utilisateur > copier l'identifiant."
                    )
                    return

        # now the player is filled with attributes
        response["creator_discord_id"] = str(ctx.author.id)
        response["name"] = response["name"].rstrip()
        await self.confirm_create_player(ctx, response)

    async def do_link(self, ctx, pseudo, discord_id):
        discord_url = "{0}?by_discord_id={1}".format(self.api_url("players"), discord_id)
        async with self._session.get(discord_url) as r:
            users = await r.json()
            if await r.json() != []:
                users = Map(users[0])
                embed = discord.Embed(title="Un joueur est déjà associé à ce compte Discord. Contactez un admin pour dissocier ce compte Discord de ce joueur.")
                self.embed_player(embed, users)
                await ctx.send(embed=embed)
                return
        player_url = "{0}?by_name_like={1}".format(self.api_url("players"), pseudo)
        async with self._session.get(player_url) as r:
            result = await r.json()
        if len(result) == 0:
            embed = discord.Embed(title="Ce pseudo n'existe pas.\nUtilisez la commande `!ajouterjoueur` pour l'ajouter.\n")
            await ctx.send(embed=embed)
            return
        if len(result) == 1:
            users = result[0]
            embed = discord.Embed(
                title="Joueur trouvé :",
                colour=discord.Colour(0xA54C4C),
            )
            self.embed_player(embed, users)
            temp_message = await ctx.send(embed=embed)
            pred = ReactionPredicate.yes_or_no(temp_message, ctx.author)
            start_adding_reactions(
                temp_message, ReactionPredicate.YES_OR_NO_EMOJIS
            )
            try:
                await self.bot.wait_for(
                    "reaction_add", timeout=60.0, check=pred
                )
            except asyncio.TimeoutError:
                await ctx.send("Commande annulée")
            if pred.result is True:
                await temp_message.delete()
                player_url = "{0}/{1}".format(self.api_url("players"), users["id"])
                response = {"player": {"discord_id": str(discord_id)}}
                print(player_url)
                print(response)
                async with self._session.patch(player_url, json=response) as r:
                    embed = discord.Embed(
                        title=f"\"I guess it's done!\".\nLe compte Discord {discord_id} est maintenant associé au joueur {pseudo}.",
                        colour=discord.Colour(0xA54C4C),
                    )
                    await ctx.send(embed=embed)
                    return
            else:
                await ctx.send("Commande annulée")
                await temp_message.delete()
                return
        else:
            embed = discord.Embed(
                title="Plusieurs joueurs ont ce pseudo.\nChoisissez le bon joueur dans la liste ci-dessous grâce aux réactions",
                colour=discord.Colour(0xA54C4C),
            )
            self.embed_players(embed, result, with_index=True)
            temp_message = await ctx.send(embed=embed)
            emojis = ReactionPredicate.NUMBER_EMOJIS[1:len(result) + 1]
            start_adding_reactions(temp_message, emojis)
            pred = ReactionPredicate.with_emojis(emojis, temp_message)
            try:
                await ctx.bot.wait_for("reaction_add", timeout=60.0, check=pred)
            except asyncio.TimeoutError:
                await ctx.send("Commande annulée")
            if type(pred.result) == int:
                await temp_message.delete()
                player_url = "{0}/{1}".format(self.api_url("players"), result[pred.result]["id"])
                async with self._session.get(player_url) as r:
                    result = await r.json()
                    if result["discord_id"] == None:
                        response = {"player": {"discord_id": str(discord_id)}}
                        await self._session.patch(player_url, json=response)
                        embed = discord.Embed(
                            title=f"\"I guess it's done!\".\nLe compte Discord {discord_id} est maintenant associé au joueur {pseudo}.",
                            colour=discord.Colour(0xA54C4C),
                        )
                        await ctx.send(embed=embed)
                    else:
                        embed = discord.Embed(
                            title=f"Il semblerait que ce joueur soit déjà associé à un compte Discord "
                        )
                        await ctx.send(embed=embed)

    async def do_unlink(self, ctx, target_member):
        discord_id = target_member.id
        discord_url = "{0}?by_discord_id={1}".format(self.api_url("players"), discord_id)
        async with self._session.get(discord_url) as r:
            users = await r.json()
            if await r.json() != []:
                users = Map(users[0])
                embed = discord.Embed(title="Un joueur est associé à ce compte discord. Voulez vous le dissocier ?")
                embed.set_footer(text="Réagissez avec ✅ pour confirmer et dissocier ce compte du joueur, ou\nréagissez avec ❎ pour annuler.")
                self.embed_player(embed, users)
                temp_message = await ctx.send(embed=embed)
                pred = ReactionPredicate.yes_or_no(temp_message, ctx.author)
                start_adding_reactions(
                    temp_message, ReactionPredicate.YES_OR_NO_EMOJIS
                )
                try:
                    await self.bot.wait_for(
                        "reaction_add", timeout=60.0, check=pred
                    )
                except asyncio.TimeoutError:
                    await ctx.send("Commande annulée")
                    return
                if pred.result is True:
                    await temp_message.delete()
                    player_url = "{0}/{1}".format(self.api_url("players"), users.id)
                    response = {"player": {"discord_id": None}}
                    await self._session.patch(player_url, json=response)
                    embed = discord.Embed(
                    title=f"\"I guess it's done!\".\nLe compte Discord {discord_id} a été dissocié du joueur {users.name}.",
                    colour=discord.Colour(0xA54C4C),
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Commande annulée")
                    await temp_message.delete()
                    return

    async def do_massadd(self, ctx, arguments):
        failed_lines = []
        args_split = arguments.splitlines()
        processed_players = []
        for arg in args_split:
            current_stage = 0
            alts = []
            # init de la réponse
            response = {"name": "", "character_ids": [], "creator_discord_id": ""}
            # process chaque arguments individuelement
            x = arg.split()
            loop = 1
            for argu in x:
                if current_stage == 0:
                    if re.search(r"<a?:(\w+):(\d+)>", argu) != None:
                        # regex les émojis discord
                        if loop == 1:
                            await uniqueyeet(
                                ctx, "Veuillez commencer par donner le nom du joueur.", x
                            )
                            break
                        else:
                            current_stage = 1
                            characters = await self.fetch_characters()
                            # associer les ID des émojis input aux id de personnages
                            emoji_dict = {}
                            for sub in characters:
                                if sub["emoji"] == re.search(r"[0-9]+", argu).group():
                                    emoji_dict = sub
                                    break
                            if emoji_dict == {}:
                                await uniqueyeet(
                                    ctx,
                                    "Veuillez utiliser les bon émojis de perso du serveur.", x
                                )
                                break
                            response["character_ids"].append(emoji_dict["id"])
                            continue
                    else:
                        # parse le nom qui peut contenir des espaces
                        response["name"] = response["name"] + argu + " "
                        loop += 1
                        name_storing = response["name"]
                        continue
                elif current_stage == 1:
                    # test si il reste des emojis a process dans les arguments
                    if re.search(r"<a?:(\w+):(\d+)>", argu) == None:
                        current_stage = 2
                        continue
                    # associer les ID des émojis input aux id de personnages si plus d'un perso est input
                    else:
                        for sub in result:
                            if sub["emoji"] == re.search(r"[0-9]+", argu).group():
                                emoji_dict = sub
                                break
                        if emoji_dict == {}:
                            await uniqueyeet(
                                ctx, "Veuillez utiliser les bon émojis de perso du serveur.", x
                            )
                            break
                        response["character_ids"].append(emoji_dict["id"])
                        continue
                # parse la team si il y en a une
                if current_stage == 2:
                    # check si l'argu est une id discord
                    if argu.isdigit() == True and len(str(argu)) == 18:
                        response["discord_id"] = str(argu)
                        break
                    async with self._session.get(self.api_url("teams")) as r:
                        result = await r.json()
                        for i in result:
                            if i["short_name"].lower() == argu.lower():
                                response["team_id"] = i["id"]
                                break
                        if "team_id" not in response:
                            # check si une ville est trouvé si aucune team l'est
                            async with self._session.get(self.api_url("cities")) as r:
                                result = await r.json()
                                for i in result:
                                    if i["name"].lower() == argu.lower():
                                        response["city_id"] = i["id"]
                                        break
                            if "city_id" not in response:
                                await uniqueyeet(
                                    ctx,
                                    "Veuillez entrer un nom de team correct.\nPour ça, utilisez son tag.\nExample : `LoS` ou `RB`", x
                                )
                                break
                            else:
                                current_stage = 4
                                continue
                    current_stage = 3
                    continue
                elif current_stage == 3:
                    # pareil, id discord
                    if argu.isdigit() == True and len(str(argu)) == 18:
                        response["discord_id"] = str(argu)
                        break
                    async with self._session.get(self.api_url("cities")) as r:
                        result = await r.json()
                        for i in result:
                            if i["name"].lower() == argu.lower():
                                response["city_id"] = i["id"]
                                break
                        if "city_id" not in response:
                            await uniqueyeet(
                                ctx,
                                "Veuillez entrer un nom de ville correct.\nSi votre ville n'éxiste pas encore, demandez a un admin de l'ajouter.", x
                            )
                            break
                    current_stage = 4
                    continue
                elif current_stage == 4:
                    if argu.isdigit() == True and len(str(argu)) == 18:
                        response["discord_id"] = str(argu)
                    else:
                        await uniqueyeet(
                            ctx,
                            "veuillez entrer l'id discord du joueur à ajouter.\nPour avoir son ID, activez simplement les options de développeur dans l'onglet apparence de discord, puis faites clic droit sur l'utilisateur > copier l'id.", x
                        )
                        break
                loop += 1
            processed_players.append(name_storing)
            # verifier que plusieurs personnes n'aient pas le même pseudo (changé D:)
            response["creator_discord_id"] = str(ctx.author.id)
            response["name"] = response["name"].rstrip()
            response = {"player": response}
            async with self._session.post(self.api_url("players"), json=response) as r:
                if r.status == 422:
                    result = await r.json()
                    erreur = Map(result)
                    print(erreur.errors["name"])
                    if erreur.errors["name"] == "already_known":
                        for i in erreur.errors["existing_ids"]:
                            player_url = self.api_url("players")
                            player_url += "/"
                            player_url += str(i)
                            async with self._session.get(player_url) as r:
                                print(await r.json())
                                result = await r.json()
                                alts.append(result)
                                print(alts)
                        embed = discord.Embed(
                            title="une ou plusieurs personnes possèdent le même pseudo que la personne que vous souhaitez ajouter. ",
                            colour=discord.Colour(0xA54C4C),
                        )
                        self.embed_players(embed, alts)
                        temp_message = await ctx.send(embed=embed)
                        pred = ReactionPredicate.yes_or_no(temp_message, ctx.author)
                        start_adding_reactions(
                            temp_message, ReactionPredicate.YES_OR_NO_EMOJIS
                        )
                        try:
                            await self.bot.wait_for(
                                "reaction_add", timeout=60.0, check=pred
                            )
                            break
                        except asyncio.TimeoutError:
                            await ctx.send("Commande annulée")
                        if pred.result is True:
                            await temp_message.delete()
                            response["player"]["name_confirmation"] = True
                            print(response)
                            async with self._session.post(self.api_url("players"), json=response) as r:
                                print(r)
                        else:
                            await ctx.send("Commande annulée")
                            await temp_message.delete()
                            break
                    else:
                        await generic_error(ctx, erreur)
                        break

    # -------------------------------------------------------------------------
    # COMMANDS
    # -------------------------------------------------------------------------

    @commands.command(usage="<nom>")
    async def ajouterville(self, ctx, *, name):
        """cette commande va vous permettre d'ajouter une ville dans la Smashthèque.
        \n\nVous devez préciser son nom.
        \n\n\nExemples : \n- !ajouterville Paris\n- !ajouterville Lyon\n"""

        try:
            await self.do_addcity(ctx, name)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<pseudo> <emotes de persos> [team] [ville] [ID Discord]")
    async def ajouterjoueur(self, ctx, *, arg):
        """cette commande va vous permettre d'ajouter un joueur dans la Smashthèque.
        \n\nVous devez ajouter au minimum le pseudo et les personnages joués (dans l'ordre).
        \n\nVous pouvez aussi ajouter sa team, sa ville et, s'il possède un compte Discord, son ID pour qu'il puisse modifier lui-même son compte.
        \n\nVous pouvez récupérer l'ID avec les options de developpeur (activez-les dans l'onglet Apparence des paramètres de l'utilisateur, puis faites un clic droit sur l'utilisateur et sélectionnez \"Copier ID\".)
        \n\n\nExemples : \n- !ajouterjoueur Pixel <:Yoshi:737480513744273500> <:Bowser:737480497332224100>\n- !ajouterjoueur red <:Joker:737480520052637756> LoS Paris 332894758076678144\n"""
        """
        current_stage représente l'argument a process.
        0 = le nom
        1 = les émojis de perso
        2 = la team
        3 = la ville
        4 = l'id discord
        """

        try:
            await self.do_addplayer(ctx, arg)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command(usage="<pseudo>")
    async def jesuis(self, ctx, *, pseudo):
        """cette commande va vous permettre d'associer votre compte Discord à un joueur de la Smashthèque.
        \n\nVous devez préciser un pseudo.
        \n\n\nExemples : \n- !jesuis Pixel\n- !jesuis red\n"""

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
        \n\n\nExemples : \n- !associer Pixel 608210202952466464\n- !associer red 332894758076678144\n"""

        try:
            args = arg.split()
            pseudo = ' '.join(args[:-1])
            discord_id = args[-1]
            await self.do_link(ctx, pseudo, discord_id)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    @commands.is_owner()
    async def jenesuispas(self, ctx):
        """cette commande permet de dissocier votre compte Discord d'un joueur de la Smashthèque.
        \n\n\nExemples : \n- !jenesuispas\n"""

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
        \n\n\nExemples : \n- !dissocier 608210202952466464\n- !dissocier 332894758076678144\n"""

        try:
            await self.do_unlink(ctx, target_member)
        except:
            rollbar.report_exc_info()
            raise

    @commands.command()
    @commands.is_owner()
    async def massadd(self, ctx, *, arguments):
        """cette commande va vous permettre d'ajouter **plusieurs** joueurs dans la base de données de smashthèque.
        \n\nAjoutez chaque joueurs normalement avec un retour à la ligne entre chacuns (maj + entré)
        \n\nVous devez ajouter au minimum le pseudo et les persos joués dans l'ordre.
        \n\nVous pouvez aussi ajouter sa team, sa ville, et si il possède un compte discord, son id pour qu'il puisse modifier lui-même son compte.
        \n\nVous pouvez récupérer l'id avec les options de developpeur (activez-les dans l'onglet Apparence des paramètres de l'utilisateur, puis faites un clic droit sur l'utilisateur et sélectionnez \"Copier ID\".)
        \n\n\nExamples :
        \n- !massadd Pixel <:Yoshi:737480513744273500> <:Bowser:737480497332224100>
        \nred <:Joker:737480520052637756> LoS Paris 332894758076678144\n"""

        try:
            await self.do_massadd(ctx, arguments)
        except:
            rollbar.report_exc_info()
            raise

