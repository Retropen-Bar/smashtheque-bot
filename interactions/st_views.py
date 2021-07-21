from discord.ext import commands

import discord
from discord import ButtonStyle

import utils

class CancellButton(discord.ui.Button["AskChoice"]):
    def __init__(self, *, label: str, number: int, style: ButtonStyle) -> None:
        #number is used to return the result of the user input
        self.number = number
        super().__init__(style=style, label=label, disabled=False)
    
    async def callback(self, interaction: discord.Interaction):
        view: ChoiceButton = self.view
        view.value = self.number
        view.stop()

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


class ChoiceButton(discord.ui.Button["AskChoice"]):
    def __init__(self, *, label: str, number: int, style: ButtonStyle) -> None:
        #number is used to return the result of the user input
        self.number = number
        super().__init__(style=style, label=label, disabled=False)
    
    async def callback(self, interaction: discord.Interaction):
        view: ChoiceButton = self.view
        view.value = self.number
        view.stop()
        


class AskChoice(discord.ui.View):
    def __init__(self, choices: list):
        self.value = None
        super().__init__(timeout=500)
        print(choices)
        for i, choice in enumerate(choices):
            label = utils.textutils.trunc_text(choice["name"], 80)
            self.add_item(ChoiceButton(label=label, number = i, style=ButtonStyle.primary))

        self.add_item(CancellButton(label="Annuler", number = -1, style=ButtonStyle.danger))

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

async def ask_choice(ctx, embed:discord.Embed, choices: list):
    view = AskChoice(choices)
    temp_message = await ctx.send(embed=embed, view=view)
    # Wait for the View to stop listening for input...
    await view.wait()
    if view.value is None or view.value == -1:
        await ctx.send("Commande annulée")
        return None
    
    else:
        return view.value