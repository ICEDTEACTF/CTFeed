from typing import List, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy

from src.database.model import CustomChannel

# logger
logger = logging.getLogger("database")

# create
async def create_custom_channel(
    db:AsyncSession,
    channel_id:int
) -> Optional[CustomChannel]:
    custom_channel = CustomChannel(
        channel_id=channel_id
    )
    
    try:
        db.add(custom_channel)
        await db.commit()
        await db.refresh(custom_channel)
    except Exception as e:
        await db.rollback()
        logger.error(f"failed to write database : {str(e)}")
        return None
    
    return custom_channel

# read
async def read_custom_channel(
    db:AsyncSession,
    channel_id:Optional[int]=None,
) -> List[CustomChannel]:
    try:
        query = sqlalchemy.select(CustomChannel)
        
        if not(channel_id is None):
            query = query.where(CustomChannel.channel_id == channel_id)
        
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"failed to read database : {str(e)}")
        return []

# delete
async def delete_custom_channel(
    db:AsyncSession,
    channel_id:int
) -> int:
    try:
        stmt = sqlalchemy.delete(CustomChannel).where(CustomChannel.channel_id == channel_id)
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"failed to write database : {str(e)}")
        return 0
    
    return 1