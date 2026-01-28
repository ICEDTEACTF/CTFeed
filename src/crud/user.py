from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy

from src.database.model import User, Status, Skills, RhythmGames

# create
async def create_user(session:AsyncSession, discord_id:int) -> User:
    """
    *This function "flushes" changes. Caller has to commit changes manually.*
    
    Create an User in database.
    
    :param session:
    :param discord_id:
    
    :return User: The User that was created (relationship wasn't loaded).
    
    :raise (Exception from sqlalchemy):
    """
    # stmt
    stmt = sqlalchemy.insert(User) \
        .values({"discord_id": discord_id}) \
        .returning(User)
    
    # execute
    try:
        result = (await session.execute(stmt)).scalar_one()
        await session.flush()
        return result
    except Exception:
        raise


# read
async def read_user(session:AsyncSession, discord_id:Optional[int]=None) -> List[User]:
    """
    Read User.
    
    :param session:
    :param discord_id:
    
    :return List[User]: A list of Users.
    
    :raise (Exception from sqlalchemy):
    """
    # stmt
    stmt = sqlalchemy.select(User) \
        .options(selectinload(User.events))
    
    if discord_id is not None:
        stmt = stmt.where(User.discord_id == discord_id)
    
    # execute
    try:
        return (await session.execute(stmt)).scalars().all()
    except Exception:
        raise


# update
async def update_user(
    session:AsyncSession,
    discord_id:int,
    status:Optional[Status]=None,
    skills:Optional[List[Skills]]=None,
    rhythm_games:Optional[List[RhythmGames]]=None
) -> User:
    """
    Update User.
    
    :param session:
    :param discord_id:
    :param status:
    :param skills:
    :param rhythm_games:
    
    :return User: The User that was updated (relationship wasn't loaded).
    
    :raise (Exception from sqlalchemy):
    """
    # args
    _args = {
        "status": status,
        "skills": skills,
        "rhythm_games": rhythm_games
    }
    
    args = {}
    for k in _args:
        if _args[k] is not None:
            args[k] = _args[k]

    # stmt
    stmt = sqlalchemy.update(User) \
        .where(User.discord_id == discord_id) \
        .values(args) \
        .returning(User)
    
    # execute
    try:
        result = (await session.execute(stmt)).scalar_one()
        await session.flush()
        return result
    except Exception:
        raise