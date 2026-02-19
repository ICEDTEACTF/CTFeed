from datetime import datetime, timezone, timedelta
from typing import Optional, List, Literal
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import discord

from src.database import model
from src.bot import get_bot
from src.config import settings
from src import schema
from src import crud

# logging
logger = logging.getLogger("uvicorn")


# functions
def format_event(guild:discord.Guild, events_db:List[model.Event]) -> List[schema.Event]:
    """
    :param guild:
    :param events_db:
    
    :return List[schema.Event]: A list of formatted Events.
    """
    result:List[schema.Event] = []
    for event in events_db:
        # event attributes
        event_type:Literal["ctftime", "custom"] = "ctftime" if event.event_id is not None else "custom"
        
        now_running:Optional[bool] = None
        if event_type == "ctftime" and event.start is not None and event.finish is not None:
            time_now = int(datetime.now(timezone.utc).timestamp())
            if event.start <= time_now and event.finish >= time_now:
                now_running = True
            else:
                now_running = False
        
        # channel
        channel:Optional[schema.DiscordChannel] = None
        if event.channel_id is not None:
            discord_channel = guild.get_channel(event.channel_id)
            if isinstance(discord_channel, discord.TextChannel):
                channel = schema.DiscordChannel(
                    id=discord_channel.id,
                    jump_url=discord_channel.jump_url,
                    name=discord_channel.name
                )

        # users
        users:List[schema.UserSimple] = []
        for db_user in event.users:
            discord_user:Optional[schema.DiscordUser] = None
            member = guild.get_member(db_user.discord_id)
            if member is not None:
                discord_user = schema.DiscordUser(
                    display_name=member.display_name,
                    id=member.id,
                    name=member.name
                )
            
            users.append(schema.UserSimple(
                discord_id=db_user.discord_id,
                status=db_user.status,
                skills=db_user.skills,
                rhythm_games=db_user.rhythm_games,
                discord=discord_user
            ))

        result.append(schema.Event(
            id=event.id,
            archived=event.archived,
            event_id=event.event_id,
            title=event.title,
            start=event.start,
            finish=event.finish,
            channel_id=event.channel_id,
            channel=channel,
            scheduled_event_id=event.scheduled_event_id,
            now_running=now_running,
            type=event_type,
            users=users
        ))
    
    return result


async def get_guild() -> discord.Guild:
    bot = await get_bot()
    if (guild := bot.get_guild(settings.GUILD_ID)) is None:
        logger.critical(f"Guild (id={settings.GUILD_ID}) not found")
        raise HTTPException(500, f"Guild (id={settings.GUILD_ID}) not found")
    return guild
