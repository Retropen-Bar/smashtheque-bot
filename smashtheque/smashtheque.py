from redbot.core.utils.predicates import ReactionPredicate
from redbot.core.utils.predicates import MessagePredicate

import discord
import asyncio
import json
import math
import rollbar
import os
import sys

from random import choice

from .helpers.misc import *
from .helpers.dialogs import *


class Smashtheque:

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
                personnages.append(format_character(self.api._characters_cache[str(character_id)]))
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
                team_names.append(format_team(self.api._teams_cache[str(team_id)]))
        if len(team_names) > 0:
            embed.add_field(name="Équipes", value="\n".join(team_names), inline=True)

        location_names = []
        if "locations" in _player:
            for location in player.locations:
                location_names.append(format_location(location))
        elif "location_ids" in _player:
            for location_id in player.location_ids:
                location_names.append(format_location(self.api._locations_cache[str(location_id)]))
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
        doit = await ask_confirmation(ctx, embed)
        if doit:
            await self.create_player(ctx, player)

    async def create_player(self, ctx, player):
        print(f"create player {player}")
        r = await self.api.createPlayer(player)
        if r.status == 201:
            # player creation wen fine
            player_name = player["name"]
            await show_confirmation(ctx, f"Le joueur {player_name} a été ajouté à la Smashthèque et est en attente de validation.")
            return

        if r.status == 422:
            result = await r.json()
            erreur = Map(result)
            print(f"errors: {erreur.errors}")
            if "name" in erreur.errors and erreur.errors["name"] == "already_known":
                alts = await self.api.findPlayerByIds(erreur.errors["existing_ids"])
                embed = discord.Embed(
                    title="Un ou plusieurs joueurs possèdent le même pseudo que le joueur que vous souhaitez ajouter.",
                    colour=discord.Colour.blue()
                )
                embed.set_footer(text="Réagissez avec ✅ pour confirmer et créer un nouveau joueur, ou\nréagissez avec ❎ pour annuler.")
                self.embed_players(embed, alts)
                doit = await ask_confirmation(ctx, embed)
                if doit:
                    player["name_confirmation"] = True
                    await self.create_player(ctx, player)
            elif "discord_user" in erreur.errors and erreur.errors["discord_user"] == ["already_taken"]:
                await yeet(ctx, "Ce compte Discord est déjà relié à un autre joueur dans la Smashthèque.")
                return
            else:
                await generic_error(ctx)
                rollbar.report_exc_info(sys.exc_info(), erreur)
                return

    async def update_player(self, ctx, player_id, data):
        print(f"update player {player_id} with {data}")
        r = await self.api.updatePlayer(player_id, data)
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
                alts = await self.api.findPlayerByIds(erreur.errors["existing_ids"])
                embed = discord.Embed(
                    title="Un ou plusieurs autres joueurs utilisent ce pseudo.",
                    colour=discord.Colour.blue()
                )
                embed.set_footer(text="Réagissez avec ✅ pour confirmer et mettre à jour, ou\nréagissez avec ❎ pour annuler.")
                self.embed_players(embed, alts)
                doit = await ask_confirmation(ctx, embed)
                if doit:
                    data["name_confirmation"] = True
                    await self.update_player(ctx, player_id, data)
            elif "discord_user" in erreur.errors and erreur.errors["discord_user"] == ["already_taken"]:
                await yeet(ctx, "Ce compte Discord est déjà relié à un autre joueur dans la Smashthèque.")
                return
            else:
                await generic_error(ctx)
                rollbar.report_exc_info(sys.exc_info(), erreur)
                return

    async def complete_bracket_link(self, ctx, tournament):

        await ctx.send(f"**Lien du bracket pour l'édition du tournoi {tournament['name']} ?** (envoyez stop pour annuler)")
        try:
            message = await self.bot.wait_for('message', timeout=120.0, check=MessagePredicate.same_context(ctx))
        except asyncio.TimeoutError:
            await ctx.send("commande annulée.")
            return None
        else:
            if message.content.lower() in ["stop", "annuler", "cancel"]:
                await ctx.send("commande annulée.")
                return None
            return message.content

    async def complete_tournament_graph(self, ctx):
        """no idea how to check if the tournament has a graph"""
        await ctx.send("Si votre tournois possède un graph, veuillez réutiliser la même commande avec le lien du tournois comme argument, et le graph comme attachement.")
        return







    async def do_createlocation(self, ctx, name, country=False):
        print(f"create location {name}")
        r = await self.api.createLocation(name, country=country)
        if r.status == 201:
            # location creation went fine
            await show_confirmation(ctx, f"La localisation {name} a été ajoutée à la base de données.")
            return

        if r.status == 422:
            result = await r.json()
            erreur = Map(result)
            print(erreur.errors["name"])
            if erreur.errors["name"] == ["not_unique"]:
                await yeet(ctx, "Cette localisation existe déjà dans la Smashthèque.")
                return

        # something went wrong but we don't know what
        await generic_error(ctx)
        rollbar.report_exc_info(sys.exc_info(), r)
        return

    async def do_addplayer(self, ctx, arg):

        # fill characters cache if empty
        await self.api.initCache()

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

                if self.api.isCharacter(argu):
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

                if not self.api.isCharacter(argu):
                    # we are actually done with the emojis, so go to stage 2
                    current_stage = 2
                    # do not 'continue' here because we stil want to process @argu
                else:
                    # more emojis to parse
                    character = await self.api.findCharacterByLabel(argu)
                    if character == None:
                        await yeet(ctx, f"Perso {argu} non reconnu")
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

                team = await self.api.findTeamByShortName(argu)
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

                location = await self.api.findLocationByName(argu)
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
        player = await self.api.findPlayerByDiscordId(discord_id)
        if player != None:
            embed = discord.Embed(title="Un joueur est déjà associé à ce compte Discord. Contactez un admin pour dissocier ce compte Discord de ce joueur.")
            self.embed_player(embed, player)
            await ctx.send(embed=embed)
            return

        players = await self.api.findPlayersByNameLike(pseudo)

        # no player found
        if len(players) == 0:
            await raise_message(ctx, f"Ce pseudo n'existe pas.\nUtilisez la commande `{ctx.clean_prefix}creerjoueur` pour l'ajouter.\n")
            return

        # one player found: ask confirmation
        if len(players) == 1:
            player = players[0]
            embed = discord.Embed(
                title="Joueur trouvé :",
                colour=discord.Colour.blue()
            )
            self.embed_player(embed, player)
            doit = await ask_confirmation(ctx, embed)
            if not doit:
                return
            if player["discord_id"] != None:
                await raise_message(ctx, "Il semblerait que ce joueur soit déjà associé à un compte Discord")
                return
            await self.update_player(ctx, player["id"], {"discord_id": str(discord_id)})
            discord_user = format_discord_user(discord_id)
            await show_confirmation(ctx, f"Le compte Discord {discord_user} est maintenant associé au joueur {pseudo}.")
            return

        # multiple players found: ask which one
        embed = discord.Embed(
            title="Plusieurs joueurs ont ce pseudo.\nChoisissez le bon joueur dans la liste ci-dessous grâce aux réactions",
            colour=discord.Colour.blue()
        )
        self.embed_players(embed, players, with_index=True)
        choice = await ask_choice(ctx, embed, len(players))
        player = players[choice]
        if player["discord_id"] != None:
            await raise_message(ctx, "Il semblerait que ce joueur soit déjà associé à un compte Discord")
            return
        await self.update_player(ctx, player["id"], {"discord_id": str(discord_id)})
        discord_user = format_discord_user(discord_id)
        await show_confirmation(ctx, f"Le compte Discord {discord_user} est maintenant associé au joueur {pseudo}.")

    async def do_unlink(self, ctx, target_member):
        discord_id = target_member.id
        player = await self.api.findPlayerByDiscordId(discord_id)
        if player == None:
            await raise_not_linked(ctx)
            return
        embed = discord.Embed(title="Un joueur est associé à ce compte discord. Voulez vous le dissocier ?")
        embed.set_footer(text="Réagissez avec ✅ pour confirmer et dissocier ce compte du joueur, ou\nréagissez avec ❎ pour annuler.")
        self.embed_player(embed, player)
        doit = await ask_confirmation(ctx, embed)
        if not doit:
            return
        await self.update_player(ctx, player["id"], {"discord_id": None})
        player_name = player["name"]
        discord_user = format_discord_user(discord_id)
        await show_confirmation(ctx, f"Le compte Discord {discord_user} a été dissocié du joueur {player_name}.")

    async def do_showplayer(self, ctx, target_member):
        discord_id = target_member.id
        player = await self.api.findPlayerByDiscordId(discord_id)
        if player == None:
            await raise_not_linked(ctx)
            return
        embed = discord.Embed(
            title="Ce compte Discord est associé au joueur suivant :",
            colour=discord.Colour.green(),
        )
        self.embed_player(embed, player)
        await ctx.send(embed=embed)

    async def do_findplayer(self, ctx, name):
        players = await self.api.findPlayersByNameLike(name)

        # no player found
        if len(players) == 0:
            await raise_message(ctx, f"Aucun joueur connu avec ce pseudo.\nVous pouvez utiliser la commande `{ctx.clean_prefix}creerjoueur` pour ajouter un joueur.\n")
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
        player = await self.api.findPlayerByDiscordId(discord_id)
        if player == None:
            await raise_not_linked(ctx)
            return
        await self.update_player(ctx, player["id"], {"name": new_name})

    async def do_removelocation(self, ctx, discord_id, location_name):
        player = await self.api.findPlayerByDiscordId(discord_id)
        if player == None:
            await raise_not_linked(ctx)
            return
        location_ids = player["location_ids"]
        location = await self.api.findLocationByName(location_name)
        if location == None:
            await raise_message(
                ctx,
                f"Nous n'avons pas réussi à trouver {location_name}.\nS'il s'agit d'une ville, vous pouvez l'ajouter à la Smashthèque avec `{ctx.clean_prefix}creerville`.\nS'il s'agit d'un pays, vous pouvez l'ajouter à la Smashthèque avec `{ctx.clean_prefix}creerpays`"
            )
            return
        location_id = location["id"]
        if location_id in location_ids:
            location_ids.remove(location_id)
        await self.update_player(ctx, player["id"], {"location_ids": location_ids})

    async def do_addlocation(self, ctx, discord_id, location_name):
        player = await self.api.findPlayerByDiscordId(discord_id)
        if player == None:
            await raise_not_linked(ctx)
            return
        location_ids = player["location_ids"]
        location = await self.api.findLocationByName(location_name)
        if location == None:
            await raise_message(
                ctx,
                f"Nous n'avons pas réussi à trouver {location_name}.\nS'il s'agit d'une ville, vous pouvez l'ajouter à la Smashthèque avec `{ctx.clean_prefix}creerville`.\nS'il s'agit d'un pays, vous pouvez l'ajouter à la Smashthèque avec `{ctx.clean_prefix}creerpays`."
            )
            return
        location_id = location["id"]
        if location_id in location_ids:
            await raise_message(
                ctx,
                f"Ce joueur est déjà localisé à {location_name}."
            )
            return
        location_ids.append(location_id)
        await self.update_player(ctx, player["id"], {"location_ids": location_ids})

    async def do_removeteam(self, ctx, discord_id, team_short_name):
        player = await self.api.findPlayerByDiscordId(discord_id)
        if player == None:
            await raise_not_linked(ctx)
            return
        team_ids = player["team_ids"]
        team = await self.api.findTeamByShortName(team_short_name)
        if team == None:
            await raise_message(
                ctx,
                f"Nous n'avons pas réussi à trouver l'équipe {team_short_name}.\nVous pouvez demander à un administrateur de la créer."
            )
            return
        team_id = team["id"]
        if team_id in team_ids:
            team_ids.remove(team_id)
        await self.update_player(ctx, player["id"], {"team_ids": team_ids})

    async def do_addteam(self, ctx, discord_id, team_short_name):
        player = await self.api.findPlayerByDiscordId(discord_id)
        if player == None:
            await raise_not_linked(ctx)
            return
        team_ids = player["team_ids"]
        team = await self.api.findTeamByShortName(team_short_name)
        if team == None:
            await raise_message(
                ctx,
                f"Nous n'avons pas réussi à trouver l'équipe {team_short_name}.\nVous pouvez demander à un administrateur de la créer."
            )
            return
        team_id = team["id"]
        if team_id in team_ids:
            await raise_message(
                ctx,
                f"Ce joueur est déjà membre de l'équipe {team_short_name}."
            )
            return
        team_ids.append(team_id)
        await self.update_player(ctx, player["id"], {"team_ids": team_ids})

    async def do_listavailablecharacters(self, ctx):

        # fill characters cache if empty
        await self.api.initCache()

        lines = []
        for character_id in self.api._characters_cache:
            character = self.api._characters_cache[str(character_id)]
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
        await self.api.initCache()

        player = await self.api.findPlayerByDiscordId(discord_id)
        if player == None:
            await raise_not_linked(ctx)
            return
        character_ids = player["character_ids"]
        for label in labels.split():
            character = await self.api.findCharacterByLabel(label)
            if character == None:
                await yeet(ctx, f"Perso {label} non reconnu")
                return
            character_id = character["id"]
            if character_id in character_ids:
                character_tag = format_character(character)
                await raise_message(
                    ctx,
                    f"{character_tag} est déjà indiqué sur ce joueur."
                )
                return
            character_ids.append(character_id)
        await self.update_player(ctx, player["id"], {"character_ids": character_ids})

    async def do_removecharacters(self, ctx, discord_id, labels):

        # fill characters cache if empty
        await self.api.initCache()

        player = await self.api.findPlayerByDiscordId(discord_id)
        if player == None:
            await raise_not_linked(ctx)
            return
        character_ids = player["character_ids"]
        for label in labels.split():
            char = await self.api.findCharacterByLabel(label)
            if char == None:
                await yeet(ctx, f"Perso {label} non reconnu")
                return
            char_id = char["id"]
            if char_id in character_ids:
                character_ids.remove(char_id)
        if len(character_ids) < 1:
            await raise_message(ctx, "Un joueur doit jouer au moins un perso")
            return
        await self.update_player(ctx, player["id"], {"character_ids": character_ids})

    async def do_replacecharacters(self, ctx, discord_id, labels):

        # fill characters cache if empty
        await self.api.initCache()

        player = await self.api.findPlayerByDiscordId(discord_id)
        if player == None:
            await raise_not_linked(ctx)
            return
        character_ids = []
        for label in labels.split():
            char = await self.api.findCharacterByLabel(label)
            if char == None:
                await yeet(ctx, f"Perso {label} non reconnu")
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
        player = await self.api.findDiscordUserByDiscordId(ctx.author.id)
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
            embed = discord.Embed(title=f"Mise à jour du {object_name} de votre team", description=f"Pour changer le {object_name} de votre team, veuillez utiliser cette commande avec une image comme attachement", colour= await ctx.embed_colour())
            await ctx.send(embed=embed)
            return
        team = await self.api.findTeamById(player["administrated_teams"][0]["id"])
        if len(player["administrated_teams"]) > 1:
            embed = discord.Embed(title="Vous âtes administrateur de plusieurs teams. ", description=f"De quelle team faut-il modifier le {object_name} ?")
            for team_entry in player["administrated_teams"]:
                embed.add_field(name=team_entry["short_name"], value=team_entry["name"])
            choice_result = await ask_choice(ctx, embed, len(player["administrated_teams"]))
            team = await self.api.findTeamById(player["administrated_teams"][choice_result]["id"])
        embed = discord.Embed(title=f"Vous êtes sur le point de changer le {object_name} de la team {team['name']} pour :")
        embed.set_author(
        name="Smashthèque",
        icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
        )
        embed.set_image(url=ctx.message.attachments[0].url)
        confirmation = await ask_confirmation(ctx, embed)
        if not confirmation:
            return
        team_data = {
            f"{object_name}_url": ctx.message.attachments[0].url
        }
        response = await self.api.updateTeam(team['id'], team_data)
        if response.status != 200:
            await generic_error(ctx)
            rollbar.report_exc_info(sys.exc_info(), f"error in command majlogo : status code {response.status}, response : {response}")
            print(response)
            print(response.text)
            return
        else:
            await show_confirmation(ctx, f"Le {object_name} de la team {team['name']} a été mis à jour avec succès.")

    async def do_addedition(self, ctx, bracket):
        #generic checks
        player = await self.api.findDiscordUserByDiscordId(ctx.author.id)
        if player is None:
            await yeet(ctx, "Vous n'êtes pas enregistré dans la smashtheque.")
            return
        elif player["administrated_recurring_tournaments"] == []:
            await yeet(ctx, "Vous n'êtes l'admin d'aucun tournoi.")
            return

        #selecting the right tournament
        if len(player["administrated_recurring_tournaments"]) > 1:
            embed = discord.Embed(title="Vous êtes administrateur de plusieurs tournois.", description=f"Quel est le tournoi concerné ?")
            idx = 0
            for tournament_entry in player["administrated_recurring_tournaments"]:
                embed.add_field(name=(1+idx), value=tournament_entry["name"], inline=False)
                idx += 1
            choice = await ask_choice(ctx, embed, len(player["administrated_recurring_tournaments"]))
            if choice == None:
                return
            tournament = await self.api.findTournamentById(player["administrated_recurring_tournaments"][choice]["id"])

        else:
            tournament = await self.api.findTournamentById(player["administrated_recurring_tournaments"][0]["id"])

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
        if not await ask_confirmation(ctx, embed):
            await ctx.send("Commande annulée.")
            return
        tournament_data = {
            "recurring_tournament_id": tournament["id"],
            "bracket_url": bracket
        }
        if len(attachement) == 1:
            tournament_data["graph_url"] = attachement[0].url
        r = await self.api.createTournamentEvent(tournament_data)
        if r.status == 201:
            await show_confirmation(ctx, f"Une édition du tournois {tournament['name']} a été crée avec succès.")
        elif r.status == 200:
            await show_confirmation(ctx, f"Une édition du tournois {tournament['name']} a été modifié avec succès.")
