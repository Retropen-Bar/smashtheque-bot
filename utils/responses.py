import discord

async def respond_or_edit(ctx: discord.ApplicationContext, text = None, embed=None, attachments=None, view=None):
    """Check if the interaction has already been replied. If so, edit the message, else respond """
    kwargs = {}
    if text:
        kwargs['content'] = text
    if embed:
        kwargs['embed'] = embed
    if attachments:
        kwargs['file'] = attachments
    if view:
        kwargs['view'] = view
    
    if ctx.interaction.response.is_done():
        kwargs = {"content": "", "embed": None, "view": None}
        if text:
            kwargs['content'] = text
        if embed:
            kwargs['embed'] = embed
        if attachments:
            raise Exception("Attachments are not supported for editing")
        if view:
            kwargs['view'] = view
        await ctx.interaction.edit_original_message(**kwargs)
    else:
        await ctx.respond(**kwargs)