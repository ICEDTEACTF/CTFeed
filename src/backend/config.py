from typing import Tuple, Optional, Any
import logging

from fastapi import HTTPException
from discord.ext import commands
import discord

from src import schema
from src import crud
from src.database import model
from src.database import database
from src.config import settings, settings_lock
from src.utils.get_category import get_category

# logging
logger = logging.getLogger("uvicorn")

# functions
async def check_config_valid_obj(guild:discord.Guild, key:str, value:Any) -> Tuple[str, Any]:
    """
    Check whether the value of the config points to a valid object in Discord.
    
    :param guild:
    :param key:
    :param value:
    
    :return message:
    :return object: The object which the value of the config points to
    """
    
    config_info = model.config_info[key]
        
    msg = ""
    _ = None
    if config_info.config_type == model.ConfigType.CHANNEL and \
            (_ := guild.get_channel(value)) is not None and \
            not isinstance(_, discord.CategoryChannel):
        msg = f"Channel: {_.name}\nID: (value={value})"
    elif config_info.config_type == model.ConfigType.CATEGORY and \
            (_ := get_category(guild, value)) is not None:
        msg = f"Category: {_.name}\nID: (value={value})"
    elif config_info.config_type == model.ConfigType.ROLE and \
            (_ := guild.get_role(value)) is not None:
        msg = f"Role: {_.name}\nID: (value={value})"
    else:
        msg = f"(Invalid)\nvalue={value}"
        _ = None
        
    return msg, _


async def read_config(bot:commands.Bot, key:Optional[str]=None) -> schema.ConfigResponse:
    """
    Read config
    
    :param bot:
    :param key:
    
    :return ConfigResponse: Guild name, Guild id and Config
    
    :raise HTTPException:
    """
    # get guild
    guild = bot.get_guild(settings.GUILD_ID)
    if guild is None:
        logger.error(f"Guild (id={settings.GUILD_ID}) not found")
        raise HTTPException(500, f"Guild (id={settings.GUILD_ID}) not found")
    
    # get config
    cache_config = {}
    async with settings_lock:
        if key is not None:
            cinfo = model.config_info.get(key)
            if cinfo is None:
                raise HTTPException(404)
            
            try:
                cache_config[key] = cinfo.data_type(getattr(settings, key))
            except Exception as e:
                logger.warning(f"fail to get config (key={key}) from settings (cache): {str(e)}")
                raise HTTPException(500, f"fail to get config (key={key}) from settings (cache): {str(e)}")
        else:
            for k in model.config_info:
                try:
                    cinfo = model.config_info[k]
                    cache_config[k] = cinfo.data_type(getattr(settings, k))
                except Exception as e:
                    logger.warning(f"fail to get config (key={k}) from settings (cache): {str(e)}")
    
    # get details
    configs = []
    for k in cache_config:
        cinfo = model.config_info[k]
        v = cache_config[k]
        msg, _ = await check_config_valid_obj(guild, k, v)
        configs.append(schema.Config(
            key=k,
            description=cinfo.description,
            message=msg,
            value=v,
            ok=(True if _ is not None else False)
        ))
    
    # return
    if key is not None and len(configs) == 0:
        raise HTTPException(404)
    
    return schema.ConfigResponse(
        guild_id=settings.GUILD_ID,
        guild_name=guild.name,
        config=configs
    )


async def update_config(name:str, value:Any):
    """
    Update Config in database and cache.
    
    :params name:
    :params value:
    
    :raise: HTTPException
    """
    try:
        async with database.with_get_db() as session:
            async with session.begin():
                config = await crud.create_or_update_config(
                    session,
                    **{name.lower(): value}
                )
    except Exception as e:
        logger.error(f"fail to initialize Config in database: {str(e)}")
        raise HTTPException(500, detail=f"fail to initialize Config in database: {str(e)}")
    
    async with settings_lock:
        settings.ANNOUNCEMENT_CHANNEL_ID = config.announcement_channel_id
        settings.CTF_CHANNEL_CATEGORY_ID = config.ctf_channel_category_id
        settings.ARCHIVE_CATEGORY_ID = config.archive_category_id
        settings.PM_ROLE_ID = config.pm_role_id
        settings.MEMBER_ROLE_ID = config.member_role_id
    
    return