import discord

async def respond_or_edit(ctx: discord.ApplicationContext, text = None, embed=None, attachments=None, view=None):
    """Check if the interaction has already been replied. If so, edit the message, else respond """
    if ctx.interaction.message is None:
        await ctx.respond(text, embed=embed, file=attachments, view=view)
    else: 
        await ctx.interaction.edit_original_message( embed=embed, view=view)