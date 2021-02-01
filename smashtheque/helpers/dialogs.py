from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

import discord

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

async def generic_error(ctx):
  await yeet(ctx, "T'as cassé le bot, GG. Tu peux contacter <@332894758076678144> ou <@608210202952466464> s'il te plaît ?")

async def raise_message(ctx, message):
  embed = discord.Embed(title=message)
  embed.set_author(
    name="Smashthèque",
    icon_url="https://cdn.discordapp.com/avatars/745022618356416572/c8fa739c82cdc5a730d9bdf411a552b0.png?size=1024",
  )
  await ctx.send(embed=embed)

async def raise_not_linked(ctx):
  await raise_message(ctx, f"Votre compte Discord n'est associé à aucun joueur.\nUtilisez `{ctx.clean_prefix}jesuis` pour associer votre compte à un joueur.")

async def show_confirmation(ctx, message):
  embed = discord.Embed(
    title="I guess it's done!",
    description=message,
    colour=discord.Colour.green()
  )
  await ctx.send(embed=embed)

async def ask_confirmation(ctx, embed):
  temp_message = await ctx.send(embed=embed)
  pred = ReactionPredicate.yes_or_no(temp_message, ctx.author)
  start_adding_reactions(
    temp_message, ReactionPredicate.YES_OR_NO_EMOJIS
  )
  try:
    await ctx.bot.wait_for("reaction_add", timeout=60.0, check=pred)
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

async def ask_choice(ctx, embed, elements_count):
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
