from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
import sqlalchemy

from src.config import settings
from src.database.model import Config

# create and update
async def create_or_update_config(
    session:AsyncSession,
    announcement_channel_id:Optional[int]=None,
    ctf_channel_category_id:Optional[int]=None,
    archive_category_id:Optional[int]=None,
    pm_role_id:Optional[int]=None,
    member_role_id:Optional[int]=None
) -> Config:
    """
    *This function "flushes" changes. Caller has to commit changes manually.*
    
    Create or update a Config in database.
    
    :param session:
    :param announcement_channel_id:
    :param ctf_channel_category_id:
    :param archive_category_id:
    :param pm_role_id:
    :param member_role_id:
    
    :return: The created or updated Config
    
    :raise: (Exception from sqlalchemy)
    """
    # args
    _args = {
        "announcement_channel_id": announcement_channel_id,
        "ctf_channel_category_id": ctf_channel_category_id,
        "archive_category_id": archive_category_id,
        "pm_role_id": pm_role_id,
        "member_role_id": member_role_id,
    }
    
    args = {"id": 1}
    for k in _args:
        if _args[k] is not None:
            args[k] = _args[k]
    
    # stmt
    stmt = postgresql_insert(Config) \
        .values(args) \
        .returning(Config) \
        .on_conflict_do_update(
            index_elements=["id"],
            set_=args
        )
    
    # execute
    try:
        result = (await session.execute(stmt)).scalar_one()
        await session.flush()
        return result
    except Exception:
        raise


# read
async def read_config(session:AsyncSession) -> Config:
    """
    Read Config.
    
    Args
        session
    
    Returns
        Config
    
    Raises
        (Exceptions from sqlalchemy)
    """
    stmt = sqlalchemy.select(Config).where(Config.id == 1)
    try:
        return (await session.execute(stmt)).scalar_one()
    except Exception:
        raise
