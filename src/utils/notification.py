from typing import Optional, Literal, Union
from enum import Enum

import discord

from src.bot import get_bot
from src.config import settings

async def send_notification(
    channel_id:Union[Literal["anno"], Optional[int]],
    embed:discord.Embed,
    view:Optional[discord.ui.View]=None
) -> Optional[discord.TextChannel]:
    """
    Send notification.
    
    :param channel_id: The channel which the notification sends to (``anno`` for announcement channel).
    :param embed:
    :param view:
    
    :return discord.TextChannel: The channel which the notification sends to.
    
    :raise RuntimeError:
    """
    bot = await get_bot()
    guild = bot.get_guild(settings.GUILD_ID)
    if guild is None:
        raise RuntimeError(f"Guild (id={settings.GUILD_ID}) not found")
    
    # args
    if channel_id == "anno":
        channel = guild.get_channel(settings.ANNOUNCEMENT_CHANNEL_ID)
        if channel is None:
            raise RuntimeError(f"Announcement channel (id={settings.ANNOUNCEMENT_CHANNEL_ID}) not found")
    else:
        if channel_id is None or (channel := guild.get_channel(channel_id)) is None:
            # ignore exception and return None
            return None
    
    # send
    await channel.send(embed=embed, view=view)
    
    return channel
