# enums or lists of values for various things

number_emojis = [
    ":zero:",
    "<:icon_1:867157147451392040>",
    "<:icon_2:867157147746172958>",
    "<:icon_3:867157147943305256>",
    "<:icon_4:867157147308916756>"
]

#stolen from Red's reaction predicaments
NUMBER_EMOJIS = [
    chr(code) + "\N{COMBINING ENCLOSING KEYCAP}" for code in range(ord("0"), ord("9") + 1)
]

cancel_emoji = "<:cancel:867185099249287189>"