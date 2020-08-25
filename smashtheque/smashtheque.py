from redbot.core import commands
from redbot.core.utils.predicates import MessagePredicate
import discord
import asyncio
import aiohttp
from redbot.core.bot import Red
from typing import Optional
import re
import json

urls = {
    "characters": "https://retropen-base.herokuapp.com/api/v1/characters",
    "teams": "https://retropen-base.herokuapp.com/api/v1/teams",
    "cities": "https://retropen-base.herokuapp.com/api/v1/cities",
    "players": "https://retropen-base.herokuapp.com/api/v1/players",
}


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


async def id_to_name(id_find, url, self):
    """obsolète transformer une id arbitraire en string human freindly"""
    async with self._session.get(urls[url]) as r:
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
    end = []
    for i in id_list:
        end.append("<:placeholder:{i}>")
    return end


class Smashtheque(commands.Cog):
    async def initialize(self):
        bearer = await self.bot.get_shared_api_tokens("smashtheque")
        bearer = bearer["bearer"]
        headers = {
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
        }
        self._session = aiohttp.ClientSession(headers=headers)

    def __init__(self, bot: Red):
        self.bot = bot

    def cog_unload(self):
        asyncio.create_task(self._session.close())

    @commands.command()
    async def test3s(self, ctx):
        async with self._session.post(
            urls["players"],
            data=json.dumps(
                {
                    "player": {
                        "name": "red",
                        "character_ids": [26],
                        "creator_discord_id": "332894758076678144",
                        "team_id": 18,
                        "city_id": 24,
                    }
                }
            ),
            headers={"content-type": "application/json"},
        ) as r:
            print(r.status)

    @commands.command(usage="<pseudo> <emotes de persos> [team] [ville] [id discord]")
    @commands.is_owner()
    async def apite(self, ctx, *, arg):
        """cette commande va vous permettre d'ajouter un joueur dans la base de données de smashthèque.\n\nVous devez ajouter au minimum le pseudo et les persos joués dans l'ordre.\n\nVous pouvez aussi ajouter sa team, sa ville, et si il possède un compte discord, son id pour qu'il puisse modifier lui-même son compte.\n\nVous pouvez récupérer l'id avec les options de developpeur (activez-les dans l'onglet Apparence des paramètres de l'utilisateur, puis faites un clic droit sur l'utilisateur et sélectionnez \"Copier ID\".)\n\n\nExamples : \n- !placeholder Pixel <:Yoshi:737480513744273500> <:Bowser:747063692658737173>\n- !placeholder red <:Joker:742166628598284359> LoS Paris 332894758076678144\n"""
        print(arg)
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
        #init de la réponse
        response = {"name": "", "character_ids": [], "creator_discord_id": ""}
        #process chaque arguments individuelement
        x = arg.split()
        loop = 1
        for argu in x:
            if current_stage == 0:
                if re.search(r"<a?:(\w+):(\d+)>", argu) != None:
                    #regex les émojis discord
                    if loop == 1:
                        await yeet(
                            ctx, "Veuillez commencer par donner le nom du joueur."
                        )
                        return
                    else:
                        current_stage = 1
                        async with self._session.get(urls["characters"]) as r:
                            #associer les ID des émojis input aux id de personnages 
                            print(await r.json())
                            result = await r.json()
                            emoji_dict = {}
                            for sub in result:
                                if sub["emoji"] == re.search(r"[0-9]+", argu).group():
                                    emoji_dict = sub
                                    break
                            if emoji_dict == {}:
                                await yeet(
                                    ctx,
                                    "Veuillez utiliser les bon émojis de perso du serveur.",
                                )
                                return
                            response["character_ids"].append(emoji_dict["id"])
                            continue
                else:
                    #parse le nom qui peut contenir des espaces
                    response["name"] = response["name"] + argu
                    loop += 1
                    continue
            elif current_stage == 1:
                #test si il reste des emojis a process dans les arguments
                if re.search(r"<a?:(\w+):(\d+)>", argu) == None:
                    current_stage = 2
                    continue
                #associer les ID des émojis input aux id de personnages si plus d'un perso est input
                else:
                    for sub in result:
                        if sub["emoji"] == re.search(r"[0-9]+", argu).group():
                            emoji_dict = sub
                            break
                    if emoji_dict == {}:
                        await yeet(
                            ctx, "Veuillez utiliser les bon émojis de perso du serveur."
                        )
                        return
                    response["character_ids"].append(emoji_dict["id"])
                    continue
            #parse la team si il y en a une
            if current_stage == 2:
                #check si l'argu est une id discord
                if argu.isdigit() == True and len(str(argu)) == 18:
                    response["discord_id"] = str(argu)
                    break
                async with self._session.get(urls["teams"]) as r:
                    result = await r.json()
                    for i in result:
                        if i["short_name"].lower() == argu.lower():
                            response["team_id"] = i["id"]
                            break
                    if "team_id" not in response:
                        #check si une ville est trouvé si aucune team l'est
                        async with self._session.get(urls["cities"]) as r:
                            result = await r.json()
                            for i in result:
                                if i["name"].lower() == argu.lower():
                                    response["city_id"] = i["id"]
                                    break
                        if "city_id" not in response:
                            await yeet(
                                ctx,
                                "Veuillez entrer un nom de team correct.\nPour ça, utilisez son tag.\nExample : `LoS` ou `RB`",
                            )
                            return
                        else:
                            current_stage = 4
                            continue
                current_stage = 3
                continue
            elif current_stage == 3:
                #pareil, id discord
                if argu.isdigit() == True and len(str(argu)) == 18:
                    response["discord_id"] = str(argu)
                    break
                async with self._session.get(urls["cities"]) as r:
                    result = await r.json()
                    for i in result:
                        if i["name"].lower() == argu.lower():
                            response["city_id"] = i["id"]
                            break
                    if "city_id" not in response:
                        await yeet(
                            ctx,
                            "Veuillez entrer un nom de ville correct.\nSi votre ville n'éxiste pas encore, demandez a un admin de l'ajouter.",
                        )
                        return
                current_stage = 4
                continue
            elif current_stage == 4:
                if argu.isdigit() == True and len(str(argu)) == 18:
                    response["discord_id"] = str(argu)
                else:
                    await yeet(
                        ctx,
                        "veuillez entrer l'id discord du joueur à ajouter.\nPour avoir son ID, activez simplement les options de développeur dans l'onglet apparence de discord, puis faites clic droit sur l'utilisateur > copier l'id.",
                    )
                    return
            loop += 1
        #verifier que plusieurs personnes n'aient pas le même pseudo (obsolète, a changer)
        async with self._session.get(urls["players"]) as r:
            print(await r.json())
            result = await r.json()
            alts.append(loop_dict(result, "name", response["name"]))
            print(alts)
            if alts != [None]:
                embed = discord.Embed(
                    title="une ou plusieurs personnes possèdent le même pseudo que la personne que vous souhaitez ajouter. ",
                    colour=discord.Colour(0xA54C4C),
                )
                for users in alts:
                    async with self._session.get(urls["characters"]) as r:
                        result = await r.json()
                        alts_emojis = []
                        print(users)
                        for i in users["character_ids"]:
                            characters_result = loop_dict(result, "id", i)
                            alts_emojis.append(characters_result["emoji"])
                    formated_player = "personnages : {0}".format(
                        format_emojis(str(alts_emojis))
                    )
                    alts_team = await id_to_name(users["team_id"], "teams", self)
                    if alts_team != None:
                        formated_player = formated_player + f", Team : {alts_team}"
                    alts_ville = await id_to_name(users["city_id"], "cities", self)
                    if alts_ville != None:
                        formated_player = formated_player + f", Ville : {alts_ville}"
                    embed.add_field(
                        name="pseudo : {0}".format(users["name"]), value=formated_player
                    )
                pred = MessagePredicate.yes_or_no(ctx)
                temp_message = await ctx.send(embed=embed)
                try:
                    await self.bot.wait_for(temp_message, timeout=60.0, check=pred)
                except asyncio.TimeoutError:
                    await ctx.send("Commande annulé")
                if pred.result is True:
                    temp_message.delete()
                    return
        response["creator_discord_id"] = str(ctx.author.id)
        response = {"player": response}
        async with self._session.post(urls["players"], json=response) as r:
            print(r)
        print(response)
