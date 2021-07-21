import discord

def emoji_string_to_partial_emoji(string):
    """
    Converts a string of emoji to a partial emoji.
    """
    return discord.PartialEmoji(name=string[2:-20], id=string[-19:-2])