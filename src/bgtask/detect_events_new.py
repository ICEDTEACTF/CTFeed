from datetime import datetime, timezone, timedelta
import logging

import discord
from asyncpg.exceptions import UniqueViolationError

from src.utils import ctf_api
from src.utils import embed_creator
from src.utils import notification
from src.database import database
from src import crud
from src.config import settings

# logging
logger = logging.getLogger("uvicorn")

# function
async def _detect_events_new():
    """
    Detect new CTF Events on CTFTime
    """
    # get events from CTFTime API
    try:
        events_api = await ctf_api.fetch_ctf_events()
    except Exception as e:
        logger.error(f"fail to get CTF events from CTFTime API: {str(e)}")
        return

    # get events which are "ctftime" events and finish after now+DATABASE_SEARCH_DAYS (for example: now+(-90)) from database
    # archived=None - get both archived and non-archived events to avoid missing any events
    try:
        async with database.with_get_db() as session:
            events_db = await crud.read_event(
                session,
                type="ctftime",
                archived=None,
                finish_after=int((datetime.now(timezone.utc)+timedelta(days=settings.DATABASE_SEARCH_DAYS)).timestamp())
            )
            events_db_event_id = [event.event_id for event in events_db]
    except Exception as e:
        logger.error(f"fail to get known CTF Events from database: {str(e)}")
        return
    
    # check
    for event_api in events_api:
        event_id = event_api["id"]
        event_db_id = None
        if event_id not in events_db_event_id:
            # new CTFTime Event detected
            logger.info(f"new CTFTime Event detected: {event_api["title"]} (event_id={event_id})")
            
            # create a new Event in database
            try:
                async with database.with_get_db() as session:
                    async with session.begin():
                        event_db = await crud.create_event(
                            session=session,
                            event_id=event_id,
                            title=event_api["title"],
                            start=int(datetime.fromisoformat(event_api["start"]).astimezone(timezone.utc).timestamp()),
                            finish=int(datetime.fromisoformat(event_api["finish"]).astimezone(timezone.utc).timestamp())
                        )
                        event_db_id = event_db.id
            except UniqueViolationError:
                logger.info(f"fail to create an Event in database: UniqueViolationError, skipped...")
                continue
            except Exception as e:
                logger.error(f"fail to create an Event in database: {str(e)}")
                continue
            
            # send notification
            embed = await embed_creator.create_event_embed(event_api, "New CTF event detected!")
            view = discord.ui.View(timeout=None)
            view.add_item(
                discord.ui.Button(
                    label="Join",
                    style=discord.ButtonStyle.blurple,
                    custom_id=f"ctf_join_channel:{event_db_id}",
                    emoji="🚩"
                )
            )
            try:
                await notification.send_notification(channel_id="anno", embed=embed, view=view)
            except Exception as e:
                logger.error(f"fail to send notification to announcement channel: {str(e)}")
                # ignore exception
    
    return