from datetime import datetime, timezone, timedelta
from typing import Optional, List, Literal
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import discord

from src.schema import Event, UserSimple, DiscordUser, DiscordChannel
from src.bot import get_bot
from src.config import settings
from src import crud

# logging
logger = logging.getLogger("uvicorn")


# functions
async def get_event(
    session:AsyncSession,
    # one
    id:Optional[int]=None,
    # many
    type:Optional[Literal["ctftime", "custom"]]=None,
    archived:Optional[bool]=None
) -> List[Event]:
    """
    Get Events.
    
    :param session:
    :param id:
    :param type:
    :param archived:
    
    :return List[Event]:
    
    :raise HTTPException:
    """
    # get guild
    bot = await get_bot()
    if (guild := bot.get_guild(settings.GUILD_ID)) is None:
        logger.critical(f"Guild (id={settings.GUILD_ID}) not found")
        raise HTTPException(500, f"Guild (id={settings.GUILD_ID}) not found")
    
    # build arguments
    finish_after = int((datetime.now(timezone.utc) + timedelta(days=settings.DATABASE_SEARCH_DAYS)).timestamp())
    
    # get events from database
    try:
        async with session.begin():
            if id is not None:
                # one
                events_db = await crud.read_event(session=session, id=id)
                if len(events_db) != 1:
                    raise HTTPException(404, f"Event (id={id}) not found")
            else:
                # many
                if type not in ["ctftime", "custom"]:
                    raise HTTPException(400, "type should be ctftime or custom when id is None")
                
                events_db = await crud.read_event(
                    session=session,
                    type=type,
                    archived=archived,
                    finish_after=(finish_after if type == "ctftime" else None)
                )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"fail to read Events from database: {str(e)}")
        raise HTTPException(500, "fail to read Events from database")
    
    result:List[Event] = []
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
        channel:Optional[DiscordChannel] = None
        if event.channel_id is not None:
            discord_channel = guild.get_channel(event.channel_id)
            if isinstance(discord_channel, discord.TextChannel):
                channel = DiscordChannel(
                    id=discord_channel.id,
                    jump_url=discord_channel.jump_url,
                    name=discord_channel.name
                )

        # users
        users:List[UserSimple] = []
        for db_user in event.users:
            discord_user:Optional[DiscordUser] = None
            member = guild.get_member(db_user.discord_id)
            if member is not None:
                discord_user = DiscordUser(
                    display_name=member.display_name,
                    id=member.id,
                    name=member.name
                )
            
            users.append(UserSimple(
                discord_id=db_user.discord_id,
                status=db_user.status,
                skills=db_user.skills,
                rhythm_games=db_user.rhythm_games,
                discord=discord_user
            ))

        result.append(Event(
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
