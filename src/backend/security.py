from typing import Optional
import logging

from asyncpg.exceptions import UniqueViolationError
from fastapi import HTTPException, Request
from discord.ext import commands
import discord

from src.config import settings, settings_lock
from src.database.database import with_get_db
from src.bot import get_bot
from src import crud

# logging
logger = logging.getLogger("uvicorn")

# functions
async def check_administrator(discord_id:int) -> bool:
    """
    Check whether the user meets the following requirements:
    - In the Guild (id=GUILD_ID)
    - Administrator of the Guild
    
    :param discord_id:
    
    :return: Whether the user meets the requirements.
    """
    bot = await get_bot()
    guild = bot.get_guild(settings.GUILD_ID)
    if guild is None:
        logger.critical(f"Guild (id={settings.GUILD_ID}) not found")
        return False
    
    # check whether the user is in the guild
    member = guild.get_member(discord_id)
    if member is None:
        return False
    
    # check whether the user is an administrator of the guild
    if member.guild_permissions.administrator == False:
        return False
    
    return True


async def check_user(discord_id:int, force_pm:bool) -> discord.Member:
    """
    Check whether the user meets the following requirements:
    - In the Guild (id=GUILD_ID)
    - Has PM role or member role
    
    :param discord_id:
    :param force_pm:
    
    :return discord.Member:
    
    :raise HTTPException:
    """
    bot:commands.Bot = await get_bot()
    
    # get guild
    guild = bot.get_guild(settings.GUILD_ID)
    if guild is None:
        logger.critical(f"Guild (id={settings.GUILD_ID}) not found")
        raise HTTPException(500, f"Guild (id={settings.GUILD_ID}) not found")
    
    # get member
    member = guild.get_member(discord_id)
    if member is None:
        raise HTTPException(403)
    
    # check role
    async with settings_lock:
        member_role_id = settings.MEMBER_ROLE_ID
        pm_role_id = settings.PM_ROLE_ID
    member_role = member.get_role(member_role_id)
    pm_role = member.get_role(pm_role_id)
    if force_pm:
        if pm_role is None:
            raise HTTPException(403)
    else:
        if pm_role is None and member_role is None:
            raise HTTPException(403)
    
    return member


async def check_user_and_auto_register(
    discord_id:int,
    force_pm:bool,
    auto_register:bool,
) -> discord.Member:
    """
    Check whether the user meets the following requirements:
    - In the Guild (id=GUILD_ID) (``check_user()``)
    - Has PM role or member role (``check_user()``)
    - In database
    
    :param discord_id:
    :param force_pm:
    :param auto_register:
    
    :return discord.Member:
    
    :raise HTTPException:
    """
    # check discord
    # if the user doesn't meet the requirements, raise exception
    member = await check_user(discord_id, force_pm)
    
    try:
        async with with_get_db() as session:
            async with session.begin():
                # check database
                db_users = await crud.read_user(session, discord_id)
                if len(db_users) == 0:
                    if auto_register:
                        await crud.create_user(session, discord_id)
                    else:
                        raise HTTPException(403)
    except UniqueViolationError:
        # repeated, ignore...
        pass
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"fail to check user and auto register (discord_id={discord_id}): {str(e)}")
        raise HTTPException(500, f"fail to check user and auto register (discord_id={discord_id})")
    
    return member


# for discord
async def discord_check_administrator(interaction:discord.Interaction) -> bool:
    if not (await check_administrator(interaction.user.id)):
        await interaction.response.send_message("Forbidden", ephemeral=True)
        return False
    return True


async def discord_check_user_and_auto_register(interaction:discord.Interaction, force_pm:bool) -> Optional[discord.Member]:
    try:
        return (await check_user_and_auto_register(
            discord_id=interaction.user.id,
            force_pm=force_pm,
            auto_register=True
        ))
    except Exception:
        await interaction.response.send_message("Forbidden", ephemeral=True)
        return None


# for fastapi
async def fastapi_check_user(request:Request) -> discord.Member:
    try:
        discord_id = int(request.session["discord_id"])
    except Exception:
        raise HTTPException(401)
    
    return (await check_user_and_auto_register(discord_id, force_pm=False, auto_register=False))


async def fastapi_check_pm_user(request:Request) -> discord.Member:
    try:
        discord_id = int(request.session["discord_id"])
    except Exception:
        raise HTTPException(401)
    
    return (await check_user_and_auto_register(discord_id, force_pm=True, auto_register=False))