from typing import Optional
from datetime import datetime, timezone, timedelta
import logging

import discord

from src.database import database
from src.bot import get_bot
from src.config import settings
from src import crud

# logging
logger = logging.getLogger("uvicorn")

# functions
async def do_recover(event_db_id:int):
    # get guild
    bot = await get_bot()
    if (guild := bot.get_guild(settings.GUILD_ID)) is None:
        logger.critical(f"Guild (id={settings.GUILD_ID}) not found")
        return
    
    lock_owner_token:Optional[str] = None
    sc:Optional[discord.ScheduledEvent] = None
    need_create = False
    async with database.with_get_db() as session:
        try:
            # try to lock the Event
            lock_owner_token = await crud.try_lock_event(session, event_db_id, 120)
            if lock_owner_token is None:
                raise RuntimeError(f"Can't lock Event (id={event_db_id})")

            async with session.begin():
                # get a new event_db
                events_db = await crud.read_event(
                    session=session,
                    type="ctftime",
                    archived=False, # ensure the event isn't archived
                    id=event_db_id,
                    lock_owner_token=lock_owner_token
                )
                if len(events_db) != 1:
                    raise RuntimeError(f"Event (id={event_db_id}) not found")
                event_db = events_db[0]

                # check
                if event_db.channel_id is None:
                    # The event doesn't have a channel, so no need to create or update it's scheduled event 
                    return

                if (sc_id := event_db.scheduled_event_id) is None or \
                    (sc := guild.get_scheduled_event(sc_id)) is None:
                    need_create = True

                # update - scheduled event is exists
                if not need_create:
                    if sc.name != event_db.title or \
                            sc.location.value != f"https://ctftime.org/event/{event_db.event_id}" or \
                            int(sc.start_time.astimezone(timezone.utc).timestamp()) != event_db.start or \
                            int(sc.end_time.astimezone(timezone.utc).timestamp()) != event_db.finish:
                        logger.info(f"editing the scheduled event (id={sc_id}) of event (id={event_db.id})")
                        try:
                            sc = await sc.edit(
                                reason="event updated",
                                location=f"https://ctftime.org/event/{event_db.event_id}",
                                name=event_db.title,
                                start_time=datetime.fromtimestamp(event_db.start, timezone.utc),
                                end_time=datetime.fromtimestamp(event_db.finish, timezone.utc)
                            )
                            if sc is None:
                                raise RuntimeError("sc.edit() returned None")
                        except Exception as e:
                            logger.error(f"fail to edit scheduled event (id={sc_id}) (try to recreate): {str(e)}")
                            # try to create a new one
                            need_create = True
                            sc = None

                # create - scheduled event isn't exists or can't be edited.
                if need_create:
                    logger.info(f"(re)creating the scheduled event of event (id={event_db.id})")
                    sc = await guild.create_scheduled_event(
                        location=f"https://ctftime.org/event/{event_db.event_id}",
                        name=event_db.title,
                        start_time=datetime.fromtimestamp(event_db.start, timezone.utc),
                        end_time=datetime.fromtimestamp(event_db.finish, timezone.utc)
                    )
                    if sc is None:
                        raise RuntimeError("guild.create_scheduled_event() returned None")
                    
                    # update database
                    event_db = await crud.update_event(
                        session=session,
                        id=event_db.id,
                        lock_owner_token=lock_owner_token,
                        scheduled_event_id=sc.id
                    )
        except Exception as e:
            logger.error(f"fail to create or edit scheduled event of event (id={event_db_id}): {str(e)}")
            
            # rollback
            if need_create and sc is not None:
                try:
                    await sc.delete()
                except Exception as e:
                    logger.critical(f"fail to delete the wrong scheduled event (id={sc.id}): {str(e)}")
        finally:
            if lock_owner_token is not None:
                try:
                    await crud.unlock_event(session, event_db_id, lock_owner_token)
                except Exception as e:
                    logger.critical(f"fail to unlock Event (id={event_db_id}): {str(e)}")
    
    return


async def _recover_scheduled_events():
    """
    Detect events which are non-archived and finish after now+DATABASE_SEARCH_DAYS (for example: now+(-90))
    
    - detect whether it's scheduled event is exists and update it
    """
    async with database.with_get_db() as session:
        try:
            events_db = await crud.read_event(
                session,
                type="ctftime",
                archived=False,
                finish_after=int((datetime.now(timezone.utc) + timedelta(days=settings.DATABASE_SEARCH_DAYS)).timestamp())
            )
        except Exception as e:
            logger.error(f"fail to get known CTF events from database: {str(e)}")
            return
        events_db_id = [event.id for event in events_db]
    
    for event_db_id in events_db_id:
        await do_recover(event_db_id)
    
    return