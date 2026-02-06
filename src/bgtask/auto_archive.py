from datetime import datetime, timezone, timedelta
import logging

from src.database import database
from src.backend import channel_op
from src.config import settings
from src import crud

# logging
logger = logging.getLogger("uvicorn")

# functions
async def _auto_archive():
    """
    Find CTFTime Events which finish before now+DATABASE_SEARCH_DAYS (for example: now+(-90)) and archive them.
    """
    async with database.with_get_db() as session:
        try:
            need_archive = await crud.read_ctfime_events_need_archive(
                session,
                int((datetime.now(timezone.utc) + timedelta(days=settings.DATABASE_SEARCH_DAYS)).timestamp())
            )
        except Exception as e:
            logger.error(f"fail to get CTF events which need to be archived: {str(e)}")
            return
        need_archive_id = [event.id for event in need_archive]
    
    for event_db_id in need_archive_id:
        logger.info(f"Detected: Event (id={event_db_id}) was expired.")
        try:
            await channel_op.archive_event(event_db_id, f"Event (id={event_db_id}) was expired")
        except Exception as e:
            logger.error(f"fail to archive the expired Event (id={event_db_id}): {str(e)}")
    
    return