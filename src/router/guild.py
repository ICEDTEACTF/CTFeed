from typing import List
import logging

from fastapi import APIRouter, Depends
import discord

from src.backend.security import fastapi_check_user
from src.bot import get_guild
from src import schema

# logger
logger = logging.getLogger("uvicorn")

# router
router = APIRouter(prefix="/guild", tags=["Guild"])

@router.get("/text_channels")
async def guild_text_channels(
    member:discord.Member=Depends(fastapi_check_user),
    guild:discord.Guild=Depends(get_guild)
) -> List[schema.DiscordTextChannel]:
    results = []
    for c in guild.text_channels:
        if c.permissions_for(member).view_channel == True:
            results.append(schema.DiscordTextChannel(
                id=c.id,
                jump_url=c.jump_url,
                name=c.name
            ))
    return results


@router.get("/categories")
async def guild_categories(
    member:discord.Member=Depends(fastapi_check_user),
    guild:discord.Guild=Depends(get_guild),
) -> List[schema.DiscordCategoryChannel]:
    results = []
    for c in guild.categories:
        if c.permissions_for(member).view_channel == True:
            results.append(schema.DiscordCategoryChannel(
                id=c.id,
                jump_url=c.jump_url,
                name=c.name
            ))
    return results


@router.get("/roles")
async def guild_roles(
    member:discord.Member=Depends(fastapi_check_user),
    guild:discord.Guild=Depends(get_guild),
) -> List[schema.DiscordRole]:
    return [
        schema.DiscordRole(
            id=r.id,
            name=r.name
        ) for r in guild.roles
    ]
