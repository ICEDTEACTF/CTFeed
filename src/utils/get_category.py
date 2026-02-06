from typing import Optional

import discord

def get_category(guild:discord.Guild, category_id:int) -> Optional[discord.CategoryChannel]:
    return discord.utils.get(guild.categories, id=category_id)