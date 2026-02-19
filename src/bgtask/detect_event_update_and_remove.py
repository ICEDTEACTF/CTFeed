from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import logging

from src.database import database
from src.utils import ctf_api
from src.utils import embed_creator
from src.utils import notification
from src.config import settings
from src.bot import get_guild
from src.backend import channel_op
from src import crud

# logging
logger = logging.getLogger("uvicorn")

# functions
async def check_and_update_event(event_db_id:int, event_api:Dict[str, Any]):
    """
    Check and update an Event in database and send notifications.
    """
    ntitle = event_api["title"]
    nstart = datetime.fromisoformat(event_api["start"]).astimezone(timezone.utc)
    nfinish = datetime.fromisoformat(event_api["finish"]).astimezone(timezone.utc)
    
    lock_owner_token:Optional[str] = None
    event_db_returning = {"updated": False}
    
    # get guild
    try:
        guild = get_guild()
    except Exception:
        return
    
    # update database
    async with database.with_get_db() as session:
        # get a new event_db
        try:
            event_db, lock_owner_token = await crud.read_event_one(
                session=session,
                lock=True, duration=120,
                type="ctftime",
                archived=False, # ensoure the event isn't archived
                id=event_db_id
            )
        except crud.NotFoundError:
            logger.warning(f"Event (id={event_db_id}) not found.")
            return
        except crud.LockedError:
            logger.warning(f"Event (id={event_db_id}) was locked. Skipped...")
            return
        except Exception as e:
            logger.error(f"Can't get and lock Event (id={event_db_id}): {str(e)}")
            return

        try:
            async with session.begin():
                # check
                if event_db.title != ntitle or \
                        event_db.start != int(nstart.timestamp()) or \
                        event_db.finish != int(nfinish.timestamp()):
                    # update detected
                    logger.info(f"Detected: {ntitle} (old: {event_db.title}, id={event_db.id}, event_id={event_db.event_id}) was updated")
                    
                    # update database
                    event_db = await crud.update_event(
                        session=session,
                        id=event_db.id,
                        lock_owner_token=lock_owner_token,
                        title=ntitle,
                        start=int(nstart.timestamp()),
                        finish=int(nfinish.timestamp())
                    )
                    
                    # returning
                    event_db_returning["id"] = event_db.id
                    event_db_returning["event_id"] = event_db.event_id
                    event_db_returning["channel_id"] = event_db.channel_id
                    event_db_returning["updated"] = True

            if not event_db_returning["updated"]:
                return
            
            # send notification to announcement channel
            embed = await embed_creator.create_event_embed(event_api, "Update detected!")
            try:
                await notification.send_notification(channel_id="anno", embed=embed)
            except Exception as e:
                logger.error(f"fail to send notification to announcement channel: {str(e)}")
                # ignore exception
            
            # send notification to private channel
            try:
                await notification.send_notification(channel_id=event_db_returning["channel_id"], embed=embed)
            except Exception as e:
                logger.error(f"fail to send notification to channel (id={event_db_returning["channel_id"]}): {str(e)}")
                # ignore exception
        except Exception as e:
            logger.error(f"fail to update an Event (id={event_db_id}): {str(e)}")
        finally:
            try:
                await crud.unlock_event(session, event_db_id, lock_owner_token)
            except Exception as e:
                logger.critical(f"fail to unlock Event (id={event_db_id}): {str(e)}")
    
    return


async def remove_event(event_db_returning:Dict[str, Any]):
    """
    Archive the Event which was canceled (removed) from CTFTime, send notifications and remove it's scheduled event.
    
    :param event_db_returning:
    ```
    event_db_returning = {
        "id": ...,
        "event_id": ...,
        "title": ...,
    }
    ```
    """
    logger.info(f"Detected: {event_db_returning["title"]} (id={event_db_returning["id"]}, event_id={event_db_returning["event_id"]}) was removed")
    
    try:
        await channel_op.archive_event(
            event_db_returning["id"],
            f"Event (id={event_db_returning["id"]}) was canceled (removed) from CTFTime"
        )
    except Exception as e:
        logger.error(f"fail to archive the removed Event (id={event_db_returning["id"]}, event_id={event_db_returning["event_id"]}): {str(e)}")
    
    return


async def _detect_event_update_and_remove():
    """
    Detect events which are non-archived and finish after now+DATABASE_SEARCH_DAYS (for example: now+(-90))
    
    - update
    - remove
    """
    # get all non-archived CTFTime events from database
    try:
        async with database.with_get_db() as session:
            events_db = await crud.read_event_many(
                session=session,
                type="ctftime",
                archived=False,
                limit=None,
                finish_after=int((datetime.now(timezone.utc) + timedelta(days=settings.DATABASE_SEARCH_DAYS)).timestamp()),
                finish_before=None,
                before_id=None
            )
        
        events_db_returning = [
            {
                "id": event.id,
                "event_id": event.event_id,
                "title": event.title
            } for event in events_db
        ]
    except Exception as e:
        logger.error(f"fail to get known CTFTime Events from database: {str(e)}")
        return
    
    # check
    for event_db_returning in events_db_returning:
        try:
            events_api = await ctf_api.fetch_ctf_events(event_db_returning["event_id"])
        except Exception as e:
            logger.error(f"fail to get CTF event (event_id={event_db_returning["event_id"]}) from CTFTime API: {str(e)}")
            continue
        
        if len(events_api) == 1:
            # check update
            await check_and_update_event(event_db_returning["id"], events_api[0])
        else:
            # removed
            await remove_event(event_db_returning)
    
    return
