import logging

import discord

from src.config import settings
from src.bot import get_bot

# logging
logger = logging.getLogger("uvicorn")

# functions
async def check_administrator(member_id:int) -> bool:
    """
    Check whether the member is an administrator of the guild (id=GUILD_ID)
    
    :param member_id:
    
    :return: Whether the member meet the requirements.
    """
    bot = await get_bot()
    guild = bot.get_guild(settings.GUILD_ID)
    if guild is None:
        logger.critical(f"Guild (id={settings.GUILD_ID}) not found")
        return False
    
    # check whether the member is in the guild
    member = guild.get_member(member_id)
    if member is None:
        return False
    
    # check whether the member is an administrator of the guild
    if member.guild_permissions.administrator == False:
        return False
    
    return True


# for discord
async def discord_check_administrator(interaction:discord.Interaction) -> bool:
    if not (await check_administrator(interaction.user.id)):
        await interaction.response.send_message("Forbidden", ephemeral=True)
        return False
    return True