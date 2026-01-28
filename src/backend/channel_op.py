from typing import Optional
import logging

from fastapi import HTTPException
import discord

from src.config import settings
from src.database import database
from src.database import model
from src.utils import notification
from src.utils import get_category
from src.bot import get_bot
from src import crud

# logging
logger = logging.getLogger("uvicorn")

# functions
async def archive_event(event_db_id:int, reason:str):
    """
    Archive the Event and it's channel, send notifications and remove it's scheduled event.
    
    :param event_db_id:
    :param reason:
    
    :raise HTTPException:
    """
    lock_owner_token = None
    event_db_returning = {}
    
    # get guild
    bot = await get_bot()
    if (guild := bot.get_guild(settings.GUILD_ID)) is None:
        logger.critical(f"Guild (id={settings.GUILD_ID}) not found")
        raise HTTPException(500, f"Guild (id={settings.GUILD_ID}) not found")
    
    # get archive category
    if (archive_category := get_category.get_category(guild, settings.ARCHIVE_CATEGORY_ID)) is None:
        logger.critical(f"Archive Category (id={settings.ARCHIVE_CATEGORY_ID}) not found")
        raise HTTPException(500, f"Archive Category (id={settings.ARCHIVE_CATEGORY_ID}) not found")
    
    async with database.with_get_db() as session:
        try:
            # try to lock event
            lock_owner_token = await crud.try_lock_event(session, event_db_id, 120)
            if lock_owner_token is None:
                raise RuntimeError(f"can't lock Event (id={event_db_id})")
            
            async with session.begin():
                # get a new event_db
                events_db = await crud.read_event(
                    session=session,
                    archived=False, # ensure the Event isn't archived
                    id=event_db_id,
                    lock_owner_token=lock_owner_token,
                )
                if len(events_db) != 1:
                    raise RuntimeError(f"Event (id={event_db_id}) not found")
                event_db = events_db[0]
                
                # update database
                event_db:model.Event = await crud.update_event(
                    session=session,
                    id=event_db.id,
                    lock_owner_token=lock_owner_token,
                    archived=True
                )
                
                # returning
                event_db_returning["id"] = event_db.id
                event_db_returning["title"] = event_db.title
                event_db_returning["channel_id"] = event_db.channel_id
                event_db_returning["scheduled_event_id"] = event_db.scheduled_event_id
            
            embed = discord.Embed(
                title=f"{event_db_returning["title"]} was archived",
                description=reason,
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Event ID in database: {event_db_returning["id"]}")
            # send notification to announcement channel
            try:
                await notification.send_notification("anno", embed)
            except Exception as e:
                logger.error(f"fail to send notification to announcement channel: {str(e)}")
                # ignore exception
            
            # send notification to private channel
            # todo:
            # 目前策略是「移動頻道失敗時輸出 Log 讓管理員手動排解」
            # 但這樣仍會讓 db data 跟實際狀況不同步
            c:Optional[discord.TextChannel] = None
            try:
                c = await notification.send_notification(event_db_returning["channel_id"], embed)
            except Exception as e:
                logger.error(f"fail to send notification to channel (id={event_db_returning["channel_id"]}): {str(e)}")
                # ignore exception
            
            # move channel
            if c is not None:
                try:
                    await c.move(
                        category=archive_category,
                        beginning=True,
                        sync_permissions=True,
                        reason=f"archived: {reason}"
                    )
                except Exception as e:
                    logger.error(f"fail to move channel (id={event_db_returning["channel_id"]}) to archive category: {str(e)}")
                    # ignore exception
            
            # remove scheduled event
            if (sc_id := event_db_returning["scheduled_event_id"]) is not None and \
                (sc := guild.get_scheduled_event(sc_id)) is not None:
                    try:
                        await sc.delete()
                    except Exception as e:
                        logger.error(f"fail to remove scheduled event (id={event_db_returning["scheduled_event_id"]}): {str(e)}")
                        # ignore exception
        except Exception as e:
            logger.error(f"fail to archive Event (id={event_db_id}): {str(e)}")
            raise HTTPException(500, f"fail to archive Event (id={event_db_id})")
        finally:
            if lock_owner_token is not None:
                try:
                    await crud.unlock_event(session, event_db_id, lock_owner_token)
                except Exception as e:
                    logger.critical(f"fail to unlock Event (id={event_db_id}): {str(e)}")
    
    return
