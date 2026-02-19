from typing import List, Optional, Literal, Tuple, Union
from datetime import datetime, timedelta, timezone
import hashlib
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy

from src.database.model import Event, User, user_event
from src.config import settings

# lock and unlock
class NotFoundError(Exception):
    pass

class LockedError(Exception):
    pass

#async def read_event(
#    session:AsyncSession,
#    # lock
#    lock:bool,
#    duration:Optional[int]=None,
#    # filters
#    type:Optional[Literal["ctftime", "custom"]]=None,
#    archived:Optional[bool]=None,
#    id:Optional[int]=None,
#    channel_id:Optional[int]=None,
#    # only for CTFTime Events
#    event_id:Optional[int]=None,
#    finish_after:Optional[int]=None,
#) -> Tuple[List[Event], Optional[str]]:
#    """
#    Read Events and try to lock an Event.
#    
#    :param session:
#    :param lock: Whether to lock the Event.
#    :param duration:
#    :param type: Search "ctftime", "custom" Events, or ``None`` to search both types of Events.
#    :param archived: Search archived, non-archived Events, or ``None`` to search both types of Events.
#    :param id:
#    :param channel_id: Discord channel ID.
#    :param event_id: (CTFTime Event only) CTFTime Event id.
#    :param finish_after: (CTFTime Event only) search CTFTime Events which finish after ``finish_after``.
#    
#    :return List[Event]: A list of Events.
#    :return str: Lock owner token.
#    
#    :raise NotFoundError: Can't find the Event (when id, channel_id or event_id is not None).
#    :raise LockedError: The Event was locked.
#    :raise ValueError:
#    :raise (Exception from sqlalchemy):
#    """
#    # functions
#    def _build_filter(stmt):
#        if type is not None:
#            if type == "ctftime":
#                if event_id is not None:
#                    stmt = stmt.where(Event.event_id == event_id)
#                else:
#                    stmt = stmt.where(Event.event_id != None)
#
#                if finish_after is not None:
#                    stmt = stmt.where(Event.finish >= finish_after)
#                    
#                # sorting
#                if isinstance(stmt, sqlalchemy.Select):
#                    stmt = stmt.order_by(sqlalchemy.asc(Event.finish))
#            elif type == "custom":
#                stmt = stmt.where(Event.event_id == None)
#            else:
#                raise ValueError(f"type should be \"ctftime\", \"custom\" or None")
#        
#        if archived is not None:
#            stmt = stmt.where(Event.archived == archived)
#    
#        if id is not None:
#            stmt = stmt.where(Event.id == id)
#
#        if channel_id is not None:
#            stmt = stmt.where(Event.channel_id == channel_id)
#        
#        return stmt
#    
#    # check exists stmt
#    check_exists = sqlalchemy.select(Event) \
#        .options(selectinload(Event.users))
#    check_exists:sqlalchemy.Select = _build_filter(check_exists)
#    
#    # no need to lock -> execute and return
#    if lock == False:
#        try:
#            results = (await session.execute(check_exists)).scalars().all()
#        except Exception:
#            raise
#        if len(results) == 0:
#            raise NotFoundError
#        return results, None
#    
#    # need to lock
#    # only effective when id is not None
#    if id is None:
#        raise ValueError("id should not be None when lock is True")
#        
#    # argument check
#    if duration is None:
#        raise ValueError("duration should not be None when lock is True")
#
#    # prepare arguments
#    time_now = datetime.now(timezone.utc)
#    locked_until = time_now + timedelta(seconds=duration)
#    lock_owner_token = hashlib.sha256(os.urandom(32)).hexdigest()
#    
#    # stmt
#    check_exists_cte = check_exists.cte("check_exists_cte")
#    
#    try_lock = sqlalchemy.update(Event)
#    try_lock:sqlalchemy.Update = _build_filter(try_lock)
#    try_lock_cte = (
#        try_lock
#        .where(sqlalchemy.or_(
#            Event.locked_until == None,
#            Event.locked_until < int(time_now.timestamp())
#        ))
#        .values(
#            locked_until=int(locked_until.timestamp()),
#            locked_by=lock_owner_token
#        )
#        .returning(Event)
#    ).cte("try_lock_cte")
#    
#    check_lock = sqlalchemy.exists(
#        sqlalchemy.select(try_lock_cte.c.id) \
#        .where(try_lock_cte.c.id == id) \
#        .where(try_lock_cte.c.locked_by == lock_owner_token)
#    )
#    
#    stmt = sqlalchemy.select(
#        sqlalchemy.case(
#            (check_lock, "success"),
#            else_="locked"
#        ),
#        Event
#    ) \
#    .options(selectinload(Event.users)) \
#    .join(check_exists_cte, check_exists_cte.c.id == Event.id) \
#    .where(check_exists_cte.c.id == id)
#    
#    # execute
#    async with session.begin():
#        results = (await session.execute(stmt)).all()
#        if len(results) == 0:
#            raise NotFoundError
#        else:
#            status = results[0][0]
#            event_db = results[0][1]
#            if status == "success":
#                return [event_db], lock_owner_token
#            elif status == "locked":
#                raise LockedError
#

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
async def join_event(
    session:AsyncSession,
    event_db_id:int,
    discord_id:int,
    lock_owner_token:str
):
    """
    *This function "flushes" changes. Caller has to commit changes manually.*
    
    Join an User to an Event.
    
    :param session:
    :param event_db_id:
    :param discord_id:
    :param lock_owner_token:
    
    :raise (Exception from sqlalchemy)
    """
    time_now = datetime.now(timezone.utc)
    
    # check lock
    check_lock_stmt = sqlalchemy.select(Event.id) \
        .where(Event.id == event_db_id) \
        .where(Event.locked_by == lock_owner_token) \
        .where(Event.locked_until >= int(time_now.timestamp()))
    
    check_lock_exists_stmt = sqlalchemy.exists(check_lock_stmt)
                
    # insert
    stmt = sqlalchemy.insert(user_event).from_select(
        ["user_discord_id", "event_db_id"],
        sqlalchemy.select(discord_id, event_db_id) \
            .where(check_lock_exists_stmt)
    ).returning(user_event)
    
    # execute
    try:
        (await session.execute(stmt)).one()
        await session.flush()
        return
    except Exception:
        raise


async def delete_user_in_event(session:AsyncSession, id:int, lock_owner_token:str, discord_id:Optional[int]=None):
    """
    *This function "flushes" changes. Caller has to commit changes manually.*
    
    Remove an User (or Users) from an Event.
    
    :param session:
    :param event_db_id:
    :param lock_owner_token:
    :param discord_id:
    
    :raise (Exception from sqlalchemy):
    """
    time_now = datetime.now(timezone.utc)
    
    # check lock
    check_lock_stmt = sqlalchemy.select(Event.id) \
        .where(Event.id == id) \
        .where(Event.locked_by == lock_owner_token) \
        .where(Event.locked_until >= int(time_now.timestamp()))
    
    check_lock_exists_stmt = sqlalchemy.exists(check_lock_stmt)

    # delete
    delete_user_in_event_stmt = sqlalchemy.delete(user_event) \
        .where(user_event.c.event_db_id == id) \
        .where(check_lock_exists_stmt) \
        .returning(user_event)
    
    if discord_id is not None:
        delete_user_in_event_stmt = delete_user_in_event_stmt.where(user_event.c.user_discord_id == discord_id)
    
    delete_user_in_event_cte = delete_user_in_event_stmt.cte("delete_user_in_event_cte")

    # stmt
    stmt = sqlalchemy.select(
        sqlalchemy.case(
            (check_lock_exists_stmt, "normal"),
            else_="error"
        ),
        sqlalchemy.func.array_agg(delete_user_in_event_cte.c.user_discord_id)
    )
    
    # execute
    try:
        result = (await session.execute(stmt)).one()
        
        if result[0] != "normal":
            raise RuntimeError("Invalid lock")
        
        await session.flush()
        return
    except Exception:
        raise


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
        await session.refresh(result)
        return result
    except Exception:
        raise


# read
async def read_event_one(
    session:AsyncSession,
    id:int,
    lock:bool,
    duration:Optional[int]=None,
    type:Optional[Literal["ctftime", "custom"]]=None,
    archived:Optional[bool]=None,
) -> Tuple[Event, Optional[str]]:
    """
    Read one Event and try to lock an Event (if you want).
    
    Inside this function, it uses ``async with session.begin()``.
    
    :param session:
    :param id:
    :param lock: Whether to lock the Event.
    :param duration: How long you want to lock the Event (in seconds).
    :param type: Search ``ctftime``, ``custom`` Events, or ``None`` to search both types of Events.
    :param archived: Search archived, non-archived Events, or ``None`` to search both types of Events.
    
    :return Event:
    :return Optional[str]: Lock owner token.
    
    :raise NotFoundError: Can't find the Event.
    :raise LockedError: The Event was locked.
    :raise ValueError:
    :raise RuntimeError:
    :raise (Exception from sqlalchemy):
    """
    # functions
    def _build_filter(stmt:Union[sqlalchemy.Select, sqlalchemy.Update]) -> Union[sqlalchemy.Select, sqlalchemy.Update]:
        stmt = stmt.where(Event.id == id)
        
        if type is not None:
            if type == "ctftime":
                stmt = stmt.where(Event.event_id != None)
            elif type == "custom":
                stmt = stmt.where(Event.event_id == None)
            else:
                raise ValueError(f"type should be \"ctftime\", \"custom\" or None")
        
        if archived is not None:
            stmt = stmt.where(Event.archived == archived)
        
        return stmt

    # check exists stmt
    check_exists:sqlalchemy.Select = _build_filter(sqlalchemy.select(Event))
    
    # no need to lock -> execute and return
    if lock == False:
        check_exists = check_exists.options(selectinload(Event.users))
        async with session.begin():
            try:
                event_db = (await session.execute(check_exists)).scalar_one_or_none()
            except Exception:
                raise
            if event_db is None:
                raise NotFoundError
            return event_db, None
    
    # need to lock
    # argument check
    if duration is None:
        raise ValueError("duration should not be None when lock is True")
    
    # prepare arguments
    time_now = datetime.now(timezone.utc)
    locked_until = time_now + timedelta(seconds=duration)
    lock_owner_token = hashlib.sha256(os.urandom(32)).hexdigest()
    
    # stmt
    check_exists_cte = check_exists.cte("check_exists_cte")
    
    try_lock:sqlalchemy.Update = _build_filter(sqlalchemy.update(Event))
    try_lock_cte = (
        try_lock
        .where(sqlalchemy.or_(
            Event.locked_until == None,
            Event.locked_until < int(time_now.timestamp())
        ))
        .values(
            locked_until = int(locked_until.timestamp()),
            locked_by = lock_owner_token
        )
        .returning(Event)
    ).cte("try_lock_cte")
    
    check_lock = sqlalchemy.exists(
        sqlalchemy.select(try_lock_cte.c.id) \
        .where(try_lock_cte.c.id == id) \
        .where(try_lock_cte.c.locked_by == lock_owner_token)
    )
    
    stmt = sqlalchemy.select(
        sqlalchemy.case(
            (check_lock, "success"),
            else_="locked"
        ),
        Event
    ) \
    .options(selectinload(Event.users)) \
    .join(check_exists_cte, check_exists_cte.c.id == Event.id) \
    .where(check_exists_cte.c.id == id)

    # execute
    async with session.begin():
        results = (await session.execute(stmt)).all()
        if len(results) == 0:
            raise NotFoundError
        else:
            status = results[0][0]
            event_db = results[0][1]
            if status == "success":
                return event_db, lock_owner_token
            elif status == "locked":
                raise LockedError
            else:
                raise RuntimeError("unexpected lock status")


async def read_event_many(
    session:AsyncSession,
    type:Literal["ctftime", "custom"],
    archived:Optional[bool]=None,
    limit:Optional[int]=None,
    # ctftime events
    finish_after:Optional[int]=None,
    finish_before:Optional[int]=None,
    # ctftime events (finish_before mode) and custom events
    before_id:Optional[int]=None,
) -> List[Event]:
    """
    Read Events.
    
    There are two types of Events:
    - ``type=ctftime``
        - finish_after mode
            - Search Events which are finish after ``finish_after``
        - finish_before mode
            - Search Events (1) which are finish before ``finish_before`` (2) with id smaller than ``before_id``
            - ``finish_before`` - ``finish`` of the last event in previous page
            - ``before_id`` - ``id`` of the last event in previous page
            - ``finish_before=None`` and ``before_id=None`` for "first page"
            - ``limit`` is required
    - ``type=custom``
        - Search Events with id smaller than ``before_id``
        - ``before_id=None`` for "first page"
        - ``limit`` is required
    
    :param session:
    :param type: Search ``ctftime`` or ``custom`` Events.
    :param archived: Search archived, non-archived Events, or ``None`` to search both types of Events.
    :param limit:
    :param finish_after:
    :param finish_before:
    :param before_id:
    
    :return List[Event]: A list of Events.
    
    :raise ValueError:
    :raise (Exception from sqlalchemy):
    """
    # stmt
    stmt = sqlalchemy.select(Event) \
        .options(selectinload(Event.users))
    
    # arguments
    if type == "ctftime":
        stmt = stmt.where(Event.event_id != None) \
            .order_by(sqlalchemy.desc(Event.finish), sqlalchemy.desc(Event.id))
        
        if finish_after is not None:
            # finish_after mode
            if (finish_before is not None) or (limit is not None) or (before_id is not None):
                raise ValueError("finish_before, limit and before_id are not available for CTFTime Events in finish_after mode")
            
            stmt = stmt.where(Event.finish >= finish_after)
        else:
            # finish_before mode
            
            # limit
            if (limit is None) or (limit <= 0):
                raise ValueError("limit is required and must be greater than 0 for CTFTime Events in finish_before mode")
            
            stmt = stmt.limit(limit)
            
            # finish_before & before_id
            if (finish_before is not None) and (before_id is not None):
                stmt = stmt.where(sqlalchemy.or_(
                    Event.finish < finish_before,
                    sqlalchemy.and_(
                        Event.finish == finish_before,
                        Event.id < before_id
                    )
                ))
            else:
                if (finish_before is None) and (before_id is None):
                    # first page
                    pass
                else:
                    raise ValueError("invalid finish_before and before_id for CTFTime Events in finish_before mode")
    elif type == "custom":
        if (finish_after is not None) or (finish_before is not None):
            raise ValueError("finish_after and finish_before are not available for custom Events")

        if (limit is None) or (limit <= 0):
            raise ValueError("limit is required and must be greater than 0 for custom Events")
        
        stmt = stmt.where(Event.event_id == None) \
            .order_by(sqlalchemy.desc(Event.id)) \
            .limit(limit)
        
        if before_id is not None:
            stmt = stmt.where(Event.id < before_id)
    else:
        raise ValueError("invalid type")
    
    if archived is not None:
        stmt = stmt.where(Event.archived == archived)

    # execute
    try:
        return (await session.execute(stmt)).scalars().all()
    except Exception:
        raise


async def read_ctfime_events_need_archive(session:AsyncSession, finish_before:int) -> List[Event]:
    """
    Read Events which need to be archived.
    
    **No need to lock. This function is just for bulk reading Events.**
    
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
        result = (await session.execute(stmt)).scalar_one()
        await session.flush()
        await session.refresh(result)
        return result
    except Exception:
        raise
