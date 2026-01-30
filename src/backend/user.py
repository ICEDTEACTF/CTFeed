from datetime import datetime, timezone
from typing import Optional, List
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from src.database import model
from src.backend import security
from src.schema import User, DiscordUser, EventSimple
from src.bot import get_bot
from src.config import settings
from src import crud

# logging
logger = logging.getLogger("uvicorn")

# functions
async def get_user(session:AsyncSession, discord_id:int) -> User:
    """
    Get user.
    
    :param session:
    :param discord_id:
    
    :return schema.User:
    
    :raise HTTPException:
    """
    # get guild
    bot = await get_bot()
    if (guild := bot.get_guild(settings.GUILD_ID)) is None:
        logger.critical(f"Guild (id={settings.GUILD_ID}) not found")
        raise HTTPException(500, f"Guild (id={settings.GUILD_ID}) not found")
    
    # get user from database
    try:
        async with session.begin():
            db_users = await crud.read_user(session, discord_id)
            if len(db_users) != 1:
                raise HTTPException(404, f"User (id={discord_id}) not found")
            db_user = db_users[0]
    except Exception as e:
        logger.error(f"fail to read User (id={discord_id}) from database: {str(e)}")
        raise HTTPException(500, f"fail to read User (id={discord_id}) from database")

    member = guild.get_member(db_user.discord_id)
    
    # events
    events = []
    for event in db_user.events:
        event_type = "ctftime" if event.event_id is not None else "custom"
        
        now_running:Optional[bool] = None
        if event_type == "ctftime":
            time_now = int(datetime.now(timezone.utc).timestamp())
            if event.start <= time_now and event.finish >= time_now:
                now_running = True
            else:
                now_running = False

        event_s = EventSimple(
            id=event.id,
            archived=event.archived,
            event_id=event.event_id,
            title=event.title,
            start=event.start,
            finish=event.finish,
            channel_id=event.channel_id,
            scheduled_event_id=event.scheduled_event_id,
            now_running=now_running,
            type=event_type
        )
        
        events.append(event_s)
    
    # discord user
    discord_user:Optional[DiscordUser] = None
    if member is not None:
        discord_user = DiscordUser(
            display_name=member.display_name,
            id=member.id,
            name=member.name
        )
    
    return User(
        discord_id=db_user.discord_id,
        status=db_user.status,
        skills=db_user.skills,
        rhythm_games=db_user.rhythm_games,
        discord=discord_user,
        events=events
    )
