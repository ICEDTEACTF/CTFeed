from typing import Optional, List
from datetime import datetime, timedelta
import logging

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy

from src.database.model import Event
from src.config import settings

# logger
logger = logging.getLogger("database")

# create
async def create_event(
    db:AsyncSession,
    events:List[Event]
) -> int:
    try:
        for event in events:
            db.add(event)
        
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"failed to write database : {str(e)}")
        return 0

    return 1


# read
async def read_event(
    db:AsyncSession,
    event_id:Optional[List[int]]=None,
    channel_id:Optional[List[int]]=None,
    finish_after:Optional[int]=(datetime.now() + timedelta(days=settings.DATABASE_SEARCH_DAYS)).timestamp(),
) -> List[Event]:
    try:
        query = sqlalchemy.select(Event)
        
        if not (event_id is None):
            query = query.where(Event.event_id.in_(event_id))
        
        if not (channel_id is None):
            query = query.where(Event.channel_id.in_(channel_id))
            
        if not (finish_after is None):
            query = query.where(Event.finish >= finish_after)
            
        query = query.order_by(sqlalchemy.desc(Event.finish))
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"failed to read database : {str(e)}")
        return []


# update
async def update_event(
    db:AsyncSession,
    event_id:int,
    title:Optional[str]=None,
    start:Optional[int]=None,
    finish:Optional[int]=None,
    channel_id:Optional[int]=None
) -> Optional[Event]:
    try:
        # find
        query = sqlalchemy.select(Event).where(Event.event_id == event_id)
        event = (await db.execute(query)).scalar_one_or_none()
        if event is None:
            return None
        
        # update
        if not(title is None):
            event.title = title
        
        if not(start is None):
            event.start = start
            
        if not(finish is None):
            event.finish = finish
        
        if not(channel_id is None):
            event.channel_id = channel_id
        
        # commit
        await db.commit()
        await db.refresh(event)
        return event
    except Exception as e:
        await db.rollback()
        logger.error(f"failed to update database : {str(e)}")
        return None


# delete
async def delete_event(
    db:AsyncSession,
    event_id:List[int],
) -> int:
    try:
        stmt = sqlalchemy.delete(Event).where(Event.event_id.in_(event_id))
        await db.execute(stmt)
        
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"failed to write database : {str(e)}")
        return 0

    return 1