from typing import Optional, List, Literal
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import discord

from src.database.database import fastapi_get_db
from src.backend import security
from src.backend import channel_op
from src.backend import event as event_backend
from src import schema

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
@router.get("/")
@router.get("/{event_db_id}")
async def read_event(
    event_db_id:Optional[int]=None,
    type:Optional[Literal["ctftime", "custom"]]=None,
    archived:Optional[bool]=None,
    channel_id:Optional[int]=None,
    event_id:Optional[int]=None,
    session:AsyncSession=Depends(fastapi_get_db),
    member:discord.Member=Depends(security.fastapi_check_user)
) -> List[schema.Event]:
    try:
        events = await event_backend.get_event(
            session=session,
            type=type,
            archived=archived,
            id=event_db_id,
            channel_id=channel_id,
            event_id=event_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"fail to read Events: {str(e)}")
        raise HTTPException(500, "fail to read Events")
    
    return events


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
