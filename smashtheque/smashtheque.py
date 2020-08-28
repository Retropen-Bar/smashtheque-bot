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

api_base_url = ''
def api_url(collection):
    return f"{api_base_url}/api/v1/{collection}"


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

async def id_to_name(id_find, url, self):
    """obsolète transformer une id arbitraire en string human freindly"""
    async with self._session.get(api_url(url)) as r:
        result = await r.json()
        non_conflict_name_list = loop_dict(result, "id", id_find)
        return non_conflict_name_list["name"]


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


class Map(UserDict):
    def __getattr__(self, attr):
        val = self.data[attr]
        if isinstance(val, Mapping):
            return Map(val)
        return val


class Smashtheque(commands.Cog):
    async def initialize(self):
        global api_base_url
        if os.environ['SMASHTHEQUE_API_URL']:
            api_base_url = os.environ['SMASHTHEQUE_API_URL']
        else:
            api_base_url = await self.bot.get_shared_api_tokens("smashtheque")
            api_base_url = api_base_url["url"]
        print(f"Smashthèque API base URL set to {api_base_url}")
        if os.environ['ROLLBAR_TOKEN']:
            rollbar_token = os.environ['ROLLBAR_TOKEN']
        else:
            rollbar_token = await self.bot.get_shared_api_tokens("smashtheque")
            rollbar_token = rollbar_token["token"]
        rollbar.init(rollbar_token)
        if os.environ['SMASHTHEQUE_API_TOKEN']:
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

    def __init__(self, bot: Red):
        self.bot = bot

    def cog_unload(self):
        asyncio.create_task(self._session.close())

    async def fetch_characters(self):
        async with self._session.get(api_url("characters")) as response:
            characters = await response.json()
            # puts values in cache before responding
            for character in characters:
                self._characters_cache[character["id"]] = character
            # respond
            return characters

    def embed_player(self, embed, _player):
        print(f"embed player {_player}")
        player = Map(_player)

        alts_emojis = []
        if "characters" in _player:
            for character in player.characters:
                alts_emojis.append(character["emoji"])
        elif "character_ids" in _player:
            for character_id in player.character_ids:
                alts_emojis.append(self._characters_cache[character_id]["emoji"])
        personnages = format_emojis(alts_emojis)
        formated_player = "\u200b"

        if "team" in _player and player.team != None:
            formated_player = formated_player + "Team : {0}".format(
                player.team["name"]
            )

        if "city" in _player and player.city != None:
            formated_player = formated_player + " Ville : {0}".format(
                player.city["name"]
            )

        embed.add_field(name=player.name, value=formated_player, inline=True)
        embed.add_field(name=personnages, value="\u200b", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=False)

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
        async with self._session.post(api_url("players"), json=payload) as r:
            if r.status == 422:
                result = await r.json()
                erreur = Map(result)
                print(erreur.errors["name"])
                if erreur.errors["name"] == "already_known":
                    alts = []
                    for i in erreur.errors["existing_ids"]:
                        player_url = api_url("players")
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
                    for users in alts:
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
                        player["name_confirmation"] = True
                        await self.create_player(ctx, player)
                    else:
                        await ctx.send("Commande annulée")
                        await temp_message.delete()
                        return
                else:
                    yeet(
                        ctx,
                        "t'a cassé le bot, GG. tu peut contacter red#4356 ou Pixel#3291 s'il te plait ?",
                    )
                    rollbar.report_exc_info(sys.exc_info(), erreur)
                    return

        # player creation wen fine
        embed = discord.Embed(
            title=f"\"I guess it's done!\". Le joueur a été ajouté à la base de données.",
            colour=discord.Colour(0xA54C4C),
        )
        await ctx.send(embed=embed)

    @commands.command(usage="<pseudo> <emotes de persos> [team] [ville] [id discord]")
    async def apite(self, ctx, *, arg):
        """cette commande va vous permettre d'ajouter un joueur dans la Smashthèque.
        \n\nVous devez ajouter au minimum le pseudo et les personnages joués (dans l'ordre).
        \n\nVous pouvez aussi ajouter sa team, sa ville et, s'il possède un compte Discord, son ID pour qu'il puisse modifier lui-même son compte.
        \n\nVous pouvez récupérer l'ID avec les options de developpeur (activez-les dans l'onglet Apparence des paramètres de l'utilisateur, puis faites un clic droit sur l'utilisateur et sélectionnez \"Copier ID\".)
        \n\n\nExemples : \n- !addplayer Pixel <:Yoshi:737480513744273500> <:Bowser:737480497332224100>\n- !addplayer red <:Joker:737480520052637756> LoS Paris 332894758076678144\n"""
        """
        current_stage représente l'argument a process.
        0 = le nom
        1 = les émojis de perso
        2 = la team
        3 = la ville
        4 = l'id discord
        """

        current_stage = 0
        alts = []
        # init de la réponse
        response = {"name": "", "character_ids": [], "creator_discord_id": ""}
        # process chaque arguments individuelement
        x = arg.split()
        loop = 1
        for argu in x:
            print(f"current_stage={current_stage} argu={argu}")
            if current_stage == 0:
                if re.search(r"<a?:(\w+):(\d+)>", argu) != None:
                    # regex les émojis discord
                    if loop == 1:
                        await yeet(
                            ctx, "Veuillez commencer par donner le pseudo du joueur."
                        )
                        return
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
                            await yeet(
                                ctx,
                                "Veuillez utiliser les émojis de personnages de ce serveur.",
                            )
                            return
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
                        await yeet(
                            ctx, "Veuillez utiliser les émojis de personnages de ce serveur."
                        )
                        return
                    response["character_ids"].append(emoji_dict["id"])
                    continue
            # parse la team si il y en a une
            if current_stage == 2:
                # check si l'argu est une id discord
                if argu.isdigit() == True and len(str(argu)) == 18:
                    response["discord_id"] = str(argu)
                    break
                async with self._session.get(api_url("teams")) as r:
                    result = await r.json()
                    for i in result:
                        if i["short_name"].lower() == argu.lower():
                            response["team_id"] = i["id"]
                            break
                    if "team_id" not in response:
                        # aucune team trouvée pour ce nom, on considère que c'est une ville
                        response["city_name"] = argu
                        current_stage = 4
                        continue
                current_stage = 3
                continue
            elif current_stage == 3:
                # pareil, id discord
                if argu.isdigit() == True and len(str(argu)) == 18:
                    response["discord_id"] = str(argu)
                    break
                response["city_name"] = argu
                current_stage = 4
                continue
            elif current_stage == 4:
                if argu.isdigit() == True and len(str(argu)) == 18:
                    response["discord_id"] = str(argu)
                else:
                    await yeet(
                        ctx,
                        "veuillez entrer l'ID Discord du joueur à ajouter.\nPour avoir son ID, activez simplement les options de développeur dans l'onglet apparence de discord, puis faites un clic droit sur l'utilisateur > copier l'identifiant.",
                    )
                    return
            loop += 1
        # verifier que plusieurs personnes n'aient pas le même pseudo (obsolète, a changer)
        response["creator_discord_id"] = str(ctx.author.id)
        response["name"] = response["name"].rstrip()

        await self.confirm_create_player(ctx, response)


    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def claim(self, ctx, *, pseudo):
        discord_url = "{0}?by_discord_id={1}".format(api_url("players"), ctx.author.id)
        async with self._session.get(discord_url) as r:
            users = await r.json()
            if await r.json() != []:
                users = Map(users[0])
                embed = discord.Embed(title="Un joueur est déjà associé à votre compte Discord. Utilisez `!unclaim` pour dissocier votre compte Discord de ce joueur.")
                self.embed_player(embed, users)
                await ctx.send(embed=embed)
                return
        player_url = "{0}?by_name_like={1}".format(api_url("players"), pseudo)
        async with self._session.get(player_url) as r:
            result = await r.json()
        if len(result) == 0:
            embed = discord.Embed(title="Ce pseudo n'existe pas.\nUtilisez la commande `!addplayer` pour l'ajouter.\n")
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
                player_url = "{0}/{1}".format(api_url("players"), users.id)
                response = {"player": {"discord_id": str(ctx.author.id)}}
                print(player_url)
                print(response)
                async with self._session.patch(player_url, json=response) as r:
                    print(r)
        else:
            embed = discord.Embed(
                title="Plusieurs joueurs ont ce pseudo.\nChoisissez le bon joueur dans la liste ci-dessous grâce aux réactions",
                colour=discord.Colour(0xA54C4C),
            )
            for users in result:
                self.embed_player(embed, users)
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
                player_url = "{0}/{1}".format(api_url("players"), result[pred.result]["id"])
                async with self._session.get(player_url) as r:
                    result = await r.json()
                if result["discord_id"] == None:
                    response = {"player": {"discord_id": str(ctx.author.id)}}
                    await self._session.patch(player_url, json=response)
                    embed = discord.Embed(
                    title=f"\"I guess it's done!\". Votre compte Discord est maintenant associé au joueur nommé {pseudo}.",
                    colour=discord.Colour(0xA54C4C),
                    )
                    await ctx.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title=f"Il semblerait que ce joueur soit déjà associé à un compte Discord "
                    )
                    await ctx.send(embed=embed)
    @commands.command()
    @commands.is_owner()
    async def unclaim(self, ctx):
        discord_url = "{0}?by_discord_id={1}".format(api_url("players"), ctx.author.id)
        async with self._session.get(discord_url) as r:
            users = await r.json()
            if await r.json() != []:
                users = Map(users[0])
                embed = discord.Embed(title="Un joueur est associé avec votre compte discord. Voulez vous le dissocier ?")
                embed.set_footer(text="Réagissez avec ✅ pour confirmer et vous dissocier de ce joueur, ou\nréagissez avec ❎ pour annuler.")
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
                    player_url = "{0}/{1}".format(api_url("players"), users.id)
                    response = {"player": {"discord_id": None}}
                    await self._session.patch(player_url, json=response)
                    embed = discord.Embed(
                    title=f"\"I guess it's done!\". Votre compte Discord a été dissocié du joueur {users.name}.",
                    colour=discord.Colour(0xA54C4C),
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Commande annulée")
                    await temp_message.delete()
                    return
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
                    async with self._session.get(api_url("teams")) as r:
                        result = await r.json()
                        for i in result:
                            if i["short_name"].lower() == argu.lower():
                                response["team_id"] = i["id"]
                                break
                        if "team_id" not in response:
                            # check si une ville est trouvé si aucune team l'est
                            async with self._session.get(api_url("cities")) as r:
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
                    async with self._session.get(api_url("cities")) as r:
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
            async with self._session.post(api_url("players"), json=response) as r:
                if r.status == 422:
                    result = await r.json()
                    erreur = Map(result)
                    print(erreur.errors["name"])
                    if erreur.errors["name"] == "already_known":
                        for i in erreur.errors["existing_ids"]:
                            player_url = api_url("players")
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
                        for users in alts:
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
                            break
                        except asyncio.TimeoutError:
                            await ctx.send("Commande annulée")
                        if pred.result is True:
                            await temp_message.delete()
                            response["player"]["name_confirmation"] = True
                            print(response)
                            async with self._session.post(api_url("players"), json=response) as r:
                                print(r)
                        else:
                            await ctx.send("Commande annulée")
                            await temp_message.delete()
                            break
                    else:
                        uniqueyeet(
                            ctx,
                            "t'a cassé le bot, GG. tu peut contacter red#4356 ou Pixel#3291 s'il te plait ?", x
                        )
                        rollbar.report_exc_info(sys.exc_info(), erreur)
                        break
