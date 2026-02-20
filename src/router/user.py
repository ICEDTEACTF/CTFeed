from typing import Optional, List
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import discord

from src.backend.security import fastapi_check_user
from src.database.database import fastapi_get_db
from src.backend import user
from src import schema

# logger
logger = logging.getLogger("uvicorn")

# router
router = APIRouter(prefix="/user", tags=["User"])

# create - register (auth)
# read
# update - update_me (auth) (You can only edit yourself)
# delete - (nope)

@router.get("/")
async def read_all_user(
    session:AsyncSession=Depends(fastapi_get_db),
    member:discord.Member=Depends(fastapi_check_user)
) -> List[schema.User]:
    return (await user.get_user(session))


@router.get("/{discord_id}")
async def read_user(
    discord_id:int,
    session:AsyncSession=Depends(fastapi_get_db),
    member:discord.Member=Depends(fastapi_check_user)
) -> schema.User:
    return (await user.get_user(session, discord_id))[0]
