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
    :return object: The object which the value of the config points to.
    """
    
    config_info = model.config_info[key]
        
    msg = ""
    _ = None
    if config_info.config_type == model.ConfigType.CHANNEL and \
            (_ := guild.get_channel(value)) is not None and \
            isinstance(_, discord.TextChannel):
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
    Read config.
    
    :param bot:
    :param key:
    
    :return ConfigResponse: Guild name, Guild id and Config.
    
    :raise HTTPException:
    """
    # get guild
    guild = bot.get_guild(settings.GUILD_ID)
    if guild is None:
        logger.critical(f"Guild (id={settings.GUILD_ID}) not found")
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
                errmsg = f"fail to get config (key={key}) from settings (cache) (maybe src.database.model.Config, src.database.model.config_info and src.config are out of sync): {str(e)}"
                logger.critical(errmsg)
                raise HTTPException(500, errmsg)
        else:
            for k in model.config_info:
                try:
                    cinfo = model.config_info[k]
                    cache_config[k] = cinfo.data_type(getattr(settings, k))
                except Exception as e:
                    logger.critical(f"fail to get config (key={k}) from settings (cache) (maybe src.database.model.Config, src.database.model.config_info and src.config are out of sync): {str(e)}")
    
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


async def update_config_cache(config:model.Config):
    async with settings_lock:
        for _k in model.config_info:
            try:
                _v = getattr(config, _k.lower())
                setattr(settings, _k, _v)
            except Exception as e:
                logger.critical(f"fail to update cache of config (key={_k}) (maybe src.database.model.Config, src.database.model.config_info and src.config are out of sync): {str(e)}")


async def update_config(bot:commands.Bot, kv:Optional[Tuple]):
    """
    Update Config in database and cache.
    
    :param bot:
    :param kv: Tuple (key, value)
    
    :raise HTTPException:
    """
    # get guild
    guild = bot.get_guild(settings.GUILD_ID)
    if guild is None:
        logger.critical(f"Guild (id={settings.GUILD_ID}) not found")
        raise HTTPException(500, f"Guild (id={settings.GUILD_ID}) not found")
    
    # check arguments
    arg = {}
    if kv is not None:
        if len(kv) != 2:
            raise HTTPException(400)
        k, v = kv
        
        # check whether k is a valid config
        cinfo = model.config_info.get(k, None)
        if cinfo is None:
            raise HTTPException(400)
        
        # check whether v is valid and points to a valid object in Discord
        try:
            v = cinfo.data_type(v)
        except Exception:
            raise HTTPException(400)
        _, obj = await check_config_valid_obj(guild, k, v)
        if obj is None:
            raise HTTPException(400)
        
        # success
        arg[k.lower()] = v
    
    # update database
    try:
        async with database.with_get_db() as session:
            async with session.begin():
                config = await crud.create_or_update_config(
                    session,
                    **arg
                )
    except Exception as e:
        logger.error(f"fail to update Config in database: {str(e)}")
        raise HTTPException(500, detail=f"fail to update Config in database: {str(e)}")
    
    # update cache
    await update_config_cache(config)
    
    return