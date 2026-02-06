from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, Request, Depends
import discord

from src.backend import security
from src.backend import config as config_backend
from src.bot import get_bot
from src import schema

# logger
logger = logging.getLogger("uvicorn")

# router
router = APIRouter(prefix="/config", tags=["Config"])

# read
@router.get("/")
@router.get("/{key}")
async def read_config(
    key:Optional[str]=None,
    member:discord.Member=Depends(security.fastapi_check_administrator)
) -> schema.ConfigResponse:
    bot = await get_bot()
    try:
        config_info = await config_backend.read_config(bot, key)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"fail to read Config: {str(e)}")
        raise HTTPException(500, "fail to read Config")
    
    return config_info


# update
@router.patch("/{key}")
async def update_config(
    key:str,
    data:schema.UpdateConfig,
    member:discord.Member=Depends(security.fastapi_check_administrator),
) -> schema.General:
    # update config
    bot = await get_bot()
    try:
        await config_backend.update_config(bot, (key, data.value))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"fail to update Config (key={key}): {str(e)}")
        raise HTTPException(500, f"fail to update Config (key={key})")
    
    # logging
    logger.info(f"User {member.name} (id={member.id}) updated Config (key={key}) to value={data.value}")
    
    return schema.General(success=True, message="Done")
