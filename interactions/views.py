from discord.ext import commands

import discord

class AskConfirmation(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=500)
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Confirmer', style=discord.ButtonStyle.green, emoji=discord.PartialEmoji(name="emoji_yes", id=867082117375459340))
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.pong()
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Annuler', style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji(name="emoji_no", id=867082117782568980))
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.pong()
        self.value = False
        self.stop()

    async def ask_confirmation(ctx, embed):
        view = AskConfirmation()
        temp_message = await ctx.send(embed=embed, view=view)
        # Wait for the View to stop listening for input...
        await view.wait()
        if view.value is None:
            await ctx.send("Commande annulée")
            return False
        if view.value is True:
            await temp_message.delete()
            return True
        else:
            await ctx.send("Commande annulée")
            await temp_message.delete()
            return False