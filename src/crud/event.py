from typing import List, Optional, Literal
from datetime import datetime, timedelta, timezone
import hashlib
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy

from src.database.model import Event, user_event
from src.config import settings

# lock and unlock
async def try_lock_event(session:AsyncSession, id:int, duration:int) -> Optional[str]:
    """
    Try to lock an Event.
    
    :param session:
    :param id: The Event which you want to lock.
    :param duration: How long you want to lock the Event (in seconds).
    
    :return str: Lock owner token.
    
    :raise (Exception from sqlalchemy):
    """
    # time and lock_owner_token
    time_now = datetime.now(timezone.utc)
    locked_until = time_now + timedelta(seconds=duration)
    lock_owner_token = hashlib.sha256(os.urandom(32)).hexdigest()
    
    # stmt
    stmt = sqlalchemy.update(Event) \
        .where(Event.id == id) \
        .where(sqlalchemy.or_(
            Event.locked_until == None,
            Event.locked_until < int(time_now.timestamp()) # expired
        )) \
        .values(
            locked_until=int(locked_until.timestamp()),
            locked_by=lock_owner_token
        ) \
        .returning(Event.id)
    
    # execute
    locked = False
    async with session.begin():
        if (await session.execute(stmt)).scalar_one_or_none() is not None:
            locked = True
    
    return lock_owner_token if locked else None


async def unlock_event(session:AsyncSession, id:int, lock_owner_token:str) -> bool:
    """
    Unlock an Event.
    
    :param session:
    :param id: The Event which you want to unlock.
    :param lock_owner_token: The token which you get by calling ``try_lock_event()``.
    
    :return bool: Whether the Event is unlocked successfully or not.
    
    :raise (Exception from sqlalchemy):
    """
    # stmt
    stmt = sqlalchemy.update(Event) \
        .where(Event.id == id) \
        .where(Event.locked_by == lock_owner_token) \
        .values(
            locked_until=None,
            locked_by=None
        ) \
        .returning(Event.id)
    
    # execute
    unlocked = False
    async with session.begin():
        if (await session.execute(stmt)).scalar_one_or_none() is not None:
            unlocked = True
    
    return unlocked


# User - Event
# todo

# create
async def create_event(
    session:AsyncSession,
    # event attrbutes
    title:str,
    event_id:Optional[int]=None,
    start:Optional[int]=None,
    finish:Optional[int]=None,
) -> Event:
    """
    *This function "flushes" changes. Caller has to commit changes manually.*
    
    Create an Event in database.
    
    A CTFTime Event, which has event_id, must has the following attrbutes:
    - title
    - event_id (from CTFTime)
    - start (timestamp, from CTFTime)
    - finish (timestamp, from CTFTime)
    
    A custom Event, which doesn't have event_id, must has the following attrbutes:
    - title (as Discord channel name)
    
    :param session:
    :param title:
    :param event_id:
    :param start:
    :param finish:
    
    :return Event: The Event that was created (relationship wasn't loaded).
    
    :raise ValueError: Invalid arguments.
    :raise (Exception from sqlalchemy):
    """
    # prevent conflicting with unique key
    # CTFTime event: event_id
    # Custom event: (allow repeated title)
    
    # args
    args = {"title": title}
    
    if event_id is not None:
        # CTFTime Event
        if start is None or finish is None:
            raise ValueError("Start and finish are necessary for a CTFTime Event")
        args["event_id"] = event_id
        args["start"] = start
        args["finish"] = finish
    
    # stmt
    stmt = sqlalchemy.insert(Event) \
        .values(args) \
        .returning(Event)
    
    # execute
    try:
        result = (await session.execute(stmt)).scalar_one()
        await session.flush()
        return result
    except Exception:
        raise


# read
async def read_event(
    session:AsyncSession,
    # lock
    lock_owner_token:Optional[str]=None,
    # conditions
    type:Optional[Literal["ctftime", "custom"]]=None,
    archived:Optional[bool]=None,
    id:Optional[int]=None,
    channel_id:Optional[int]=None,
    # only for CTFTime Events
    event_id:Optional[int]=None,
    finish_after:Optional[int]=None,
) -> List[Event]:
    """
    Read Events.
    
    :param session:
    :param lock_owner_token:
    :param type: Search "ctftime", "custom" Events, or ``None`` to search both types of Events.
    :param archived: Search archived, non-archived Events, or ``None`` to search both types of Events.
    :param id:
    :param channel_id: Discord channel ID.
    :param event_id: (CTFTime Event only) CTFTime Event id.
    :param finish_after: (CTFTime Event only) search CTFTime Events which finish after ``finish_after``.
    
    :return List[Event]: A list of Events.
    
    :raise ValueError: Invalid arguments.
    :raise RuntimeError:
    :raise (Exception from sqlalchemy):
    """
    # stmt
    stmt = sqlalchemy.select(Event) \
        .options(selectinload(Event.users))
    
    # arguments
    if type is not None:
        if type == "ctftime":
            if event_id is not None:
                stmt = stmt.where(Event.event_id == event_id)
            else:
                stmt = stmt.where(Event.event_id != None)
            
            if finish_after is not None:
                stmt = stmt.where(Event.finish >= finish_after)
            
            # sorting
            stmt = stmt.order_by(sqlalchemy.asc(Event.finish))
        elif type == "custom":
            stmt = stmt.where(Event.event_id == None)
        else:
            raise ValueError(f"type should be \"ctftime\", \"custom\" or None")
    
    if archived is not None:
        stmt = stmt.where(Event.archived == archived)
    
    if id is not None:
        stmt = stmt.where(Event.id == id)
    
    if channel_id is not None:
        stmt = stmt.where(Event.channel_id == channel_id)
    
    # execute
    try:
        results = (await session.execute(stmt)).scalars().all()
    except Exception:
        raise
    
    # check lock
    if lock_owner_token is not None:
        # only effective when conditions include unique columes.
        if (id is not None or \
                channel_id is not None or \
                event_id is not None) and \
                len(results) == 1:
            result = results[0]
            
            time_now = datetime.now(timezone.utc)
            
            if result.locked_by is None or \
                    result.locked_by != lock_owner_token or \
                    result.locked_until is None or \
                    result.locked_until < int(time_now.timestamp()):
                raise RuntimeError("Invalid lock")
    
    return results


async def read_ctfime_events_need_archive(session:AsyncSession, finish_before:int) -> List[Event]:
    """
    Read Events which need to be archived.
    
    :param session:
    :param finish_before: Search Events which are non-archived and finish before ``finish_before``
    
    :return List[Event]: A list of Events.
    
    :raise (Exception from sqlalchemy):
    """
    # stmt
    stmt = sqlalchemy.select(Event) \
        .options(selectinload(Event.users)) \
        .where(Event.archived == False) \
        .where(Event.finish < finish_before)
    
    try:
        return (await session.execute(stmt)).scalars().all()
    except Exception:
        raise


# update
async def update_event(
    session:AsyncSession,
    # conditions
    id:int,
    lock_owner_token:str,
    # arguments
    archived:Optional[bool]=None,
    title:Optional[str]=None,
    start:Optional[int]=None,
    finish:Optional[int]=None,
    channel_id:Optional[int]=None,
    scheduled_event_id:Optional[int]=None
) -> Event:
    """
    *This function "flushes" changes. Caller has to commit changes manually.*
    
    Update an Event in database.
    
    :param session:
    :param id:
    :param lock_owner_token:
    :param archived:
    :param title:
    :param start:
    :param finish:
    :param channel_id:
    :param scheduled_event_id:
    
    :return Event: The Event that was updated (relationship wasn't loaded).
    
    :raise ValueError:
    :raise (Exception from sqlalchemy)
    """
    # arguments
    _args = {
        "archived": archived,
        "title": title,
        "start": start,
        "finish": finish,
        "channel_id": channel_id,
        "scheduled_event_id": scheduled_event_id
    }
    
    args = {}
    for k in _args:
        if _args[k] is not None:
            args[k] = _args[k]
    
    # stmt
    time_now = datetime.now(timezone.utc)
    
    stmt = sqlalchemy.update(Event) \
        .where(Event.id == id) \
        .where(Event.locked_by == lock_owner_token) \
        .where(Event.locked_until >= int(time_now.timestamp())) \
        .values(args) \
        .returning(Event)
    
    # execute
    try:
        return (await session.execute(stmt)).scalar_one()
    except Exception:
        raise