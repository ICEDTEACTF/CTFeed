from typing import Optional, List, Literal
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import discord

from src.database.database import fastapi_get_db
from src.backend import security
from src.backend import channel_op
from src.backend import event as event_backend
from src import schema
from src import crud

# logger
logger = logging.getLogger("uvicorn")

# router
router = APIRouter(prefix="/event", tags=["Event"])

# create
@router.post("/create_custom_event")
async def create_custom_event(
    data:schema.CreateCustomEvent,
    member:discord.Member=Depends(security.fastapi_check_user)
) -> schema.General:
    try:
        await channel_op.create_custom_event(data.title)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"fail to create custom event: {str(e)}")
        raise HTTPException(500, "fail to create custom event")
    
    return schema.General(success=True, message="Done")


# read
@router.get("/ctftime")
async def read_all_ctftime_event(
    archived:Optional[bool]=None,
    limit:int=Query(gt=0, le=20),
    finish_before:Optional[int]=Query(ge=0, default=None),
    before_id:Optional[int]=Query(ge=0, default=None),
    session:AsyncSession=Depends(fastapi_get_db),
    member:discord.Member=Depends(security.fastapi_check_user),
) -> List[schema.Event]:
    # argument check
    first_page = (finish_before is None) and (before_id is None)
    n_page = (finish_before is not None) and (before_id is not None)
    if first_page == False and n_page == False:
        raise HTTPException(400, "invalid finish_before and before_id")
    
    # get events from database
    try:
        events_db = await crud.read_event_many(
            session=session,
            type="ctftime",
            archived=archived,
            limit=limit,
            finish_after=None,
            finish_before=finish_before,
            before_id=before_id
        )
    except Exception as e:
        logger.error(f"fail to read Events from database: {str(e)}")
        raise HTTPException(500, "fail to read Events from database")
    
    # format and return
    return (await event_backend.format_event((await event_backend.get_guild()), events_db))


@router.get("/custom")
async def read_all_custom_event(
    archived:Optional[bool]=None,
    limit:int=Query(gt=0, le=20),
    before_id:Optional[int]=Query(ge=0, default=None),
    session:AsyncSession=Depends(fastapi_get_db),
    member:discord.Member=Depends(security.fastapi_check_user),
) -> List[schema.Event]:
    # get events from database
    try:
        events_db = await crud.read_event_many(
            session=session,
            type="custom",
            archived=archived,
            limit=limit,
            finish_after=None,
            finish_before=None,
            before_id=before_id
        )
    except Exception as e:
        logger.error(f"fail to read Events from database: {str(e)}")
        raise HTTPException(500, "fail to read Events from database")
    
    # format and return
    return (await event_backend.format_event((await event_backend.get_guild()), events_db))


@router.get("/{event_db_id}")
async def read_event(
    event_db_id:int,
    session:AsyncSession=Depends(fastapi_get_db),
    member:discord.Member=Depends(security.fastapi_check_user)
) -> schema.Event:
    # get event from database
    try:
        event_db, _ = await crud.read_event_one(
            session,
            lock=False,
            id=event_db_id
        )
    except crud.NotFoundError:
        raise HTTPException(404, f"Event (id={event_db_id}) not found")
    except Exception as e:
        logger.error(f"fail to read Event (id={event_db_id}) from database: {str(e)}")
        raise HTTPException(500, f"fail to read Event (id={event_db_id}) from database")
    
    # format and return
    return (await event_backend.format_event((await event_backend.get_guild()), [event_db]))[0]


# update - join
@router.patch("/{event_db_id}/join")
async def join_event(
    event_db_id:int,
    member:discord.Member=Depends(security.fastapi_check_user)
) -> schema.General:
    try:
        await channel_op.create_and_join_channel(member, event_db_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"fail to join Event (id={event_db_id}): {str(e)}")
        raise HTTPException(500, f"fail to join Event (id={event_db_id})")
    
    return schema.General(success=True, message="Done")


# update - archive
@router.patch("/{event_db_id}/archive")
async def archive_event(
    event_db_id:int,
    member:discord.Member=Depends(security.fastapi_check_pm_user)
) -> schema.General:
    try:
        await channel_op.archive_event(event_db_id, f"Manually archived by {member.name} (id={member.id})")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"fail to archive Event (id={event_db_id}): {str(e)}")
        raise HTTPException(500, f"fail to archive Event (id={event_db_id})")
    
    return schema.General(success=True, message="Done")


# update - relink
@router.patch("/{event_db_id}/relink")
async def relink_event(
    event_db_id:int,
    data:schema.RelinkEvent,
    member:discord.Member=Depends(security.fastapi_check_pm_user)
) -> schema.General:
    try:
        await channel_op.link_event_to_channel(event_db_id, data.channel_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"fail to link channel (id={data.channel_id}) to Event (id={event_db_id}): {str(e)}")
        raise HTTPException(500, f"fail to link channel (id={data.channel_id}) to Event (id={event_db_id})")
    
    return schema.General(success=True, message="Done")
