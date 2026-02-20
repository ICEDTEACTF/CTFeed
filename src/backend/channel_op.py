from typing import Optional, Dict, Any, Tuple
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
import discord

from src.config import settings
from src.database import database
from src.database import model
from src.utils import notification
from src.utils import get_category
from src.utils import ctf_api
from src.utils import embed_creator
from src.bot import get_guild
from src import crud

# channel_op = "event_op"

# logging
logger = logging.getLogger("uvicorn")

# utils
async def read_event_one_wrapper(session:AsyncSession, event_db_id:int) -> Tuple[model.Event, str]:
    try:
        event_db, lock_owner_token = await crud.read_event_one(
            session=session,
            lock=True, duration=120,
            archived=False, # ensoure the Event isn't archived
            id=event_db_id
        )
    except crud.NotFoundError:
        raise HTTPException(404, f"Event (id={event_db_id}) not found (archived, or invalid id)")
    except crud.LockedError:
        raise HTTPException(423, F"Event (id={event_db_id}) was locked. Try again later.")
    except Exception as e:
        logger.error(f"Can't get and lock Event (id={event_db_id}): {str(e)}")
        raise HTTPException(500, f"Can't get and lock Event (id={event_db_id})")
    
    return event_db, lock_owner_token


# functions
async def _create_channel(session:AsyncSession, member:discord.Member, event_db:model.Event, lock_owner_token:str) -> model.Event:
    # 在這個 function 有 exception 就直接 raise 出來
    channel:Optional[discord.TextChannel] = None
    event_api:Optional[Dict[str, Any]] = None
    ctftime_event:bool = False
    created:bool = False
    log_msg:str = ""
    
    # get guild
    guild = get_guild()
    
    # get category
    if (ctf_channel_category := get_category.get_category(guild, settings.CTF_CHANNEL_CATEGORY_ID)) is None:
        logger.critical(f"CTF channel category (id={settings.CTF_CHANNEL_CATEGORY_ID}) not found")
        raise HTTPException(500, f"CTF channel category (id={settings.CTF_CHANNEL_CATEGORY_ID}) not found")
    
    try:
        async with session.begin():
            ctftime_event = True if event_db.event_id is not None else False
            
            # check channel
            if (channel_id := event_db.channel_id) is not None and \
                    guild.get_channel(channel_id) is not None:
                # exists -> no need to create
                return event_db

            if ctftime_event:
                events_api = await ctf_api.fetch_ctf_events(event_db.event_id)
                if len(events_api) == 0:
                    raise HTTPException(404, f"Event (id={event_db.id}, event_id={event_db.event_id}) not found (CTFTime)")
                event_api = events_api[0]
            
            # delete old members
            await crud.delete_user_in_event(session, id=event_db.id, lock_owner_token=lock_owner_token)
            
            # create channel
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True)
            }
            channel = await guild.create_text_channel(name=event_db.title, category=ctf_channel_category, overwrites=overwrites)
            
            # update database
            event_db = await crud.update_event(session, event_db.id, lock_owner_token, channel_id=channel.id)
            
            created = True
            log_msg = f"{member.name} (id={member.id}) created a channel (id={channel.id}) for Event {event_db.title} (id={event_db.id})"
    except Exception as e:
        # rollback
        if channel is not None:
            try:
                await channel.delete()
            except Exception as e:
                logger.critical(f"[rollback] fail to delete the wrong TextChnnel (id={channel.id}): {str(e)}")
        
        # raise exception
        raise
    
    # logging
    logger.info(log_msg)
    
    if created:
        # send notification
        if ctftime_event:
            embed = await embed_creator.create_event_embed(event_api, f"{member.display_name} raised {event_db.title}")
        else:
            embed = discord.Embed(color=discord.Color.green(), title=f"{member.display_name} created the channel")
        try:
            await notification.send_notification(channel.id, embed)
        except Exception as e:
            logger.error(f"fail to send notification to channel (id={channel.id}): {str(e)}")
            # ignore exception

    return event_db


async def _join_channel(session:AsyncSession, member:discord.Member, event_db:model.Event, lock_owner_token:str):
    # 在這個 function 有 exception 就直接 raise 出來
    # get guild
    guild = get_guild()
    
    joined_channel = False  # joined channel in Discord, but not in database
    joined = False          # joined channel in Discord and database
    log_msg:str = ""
    try:
        async with session.begin():
            # check channel
            if (channel_id := event_db.channel_id) is None or \
                (channel := guild.get_channel(channel_id)) is None:
                raise RuntimeError(f"TextChannel for Event (id={event_db.id}) not found")
            
            # join channel
            await channel.set_permissions(member, view_channel=True)
            joined_channel = True
            
            # update database
            try:
                await crud.join_event(session, event_db.id, member.id, lock_owner_token)
            except IntegrityError:
                # ignore
                raise HTTPException(409, f"The user (discord_id={member.id}) has joined the Event (id={event_db.id})")
            except Exception:
                raise
            joined = True
            
            log_msg = f"{member.name} (id={member.id}) joined the channel {channel.name} (id={channel.id}) for Event {event_db.title} (id={event_db.id})"
    except Exception as e:
        # ignore HTTPException
        if isinstance(e, HTTPException):
            raise
        
        # rollback
        if joined_channel:
            try:
                await channel.set_permissions(member, view_channel=False)
            except Exception as e:
                logger.critical(f"[rollback] fail to set permission (view_channel=False) of channel (id={channel.id}) for member (discord_id={member.id}): {str(e)}")
        
        # raise exception
        raise
    
    # logging
    logger.info(log_msg)
    
    if joined:
        # send notification
        try:
            await notification.send_notification(channel.id, embed=discord.Embed(color=discord.Color.green(), title=f"{member.display_name} joined the channel"))
        except Exception as e:
            logger.error(f"fail to send notification to channel (id={channel.id}): {str(e)}")
            # ignore exception
    
    return


async def create_and_join_channel(member:discord.Member, event_db_id:int):
    """
    Join channel or create channel (if the channel isn't exists).
    
    :param member:
    :param event_db_id:
    
    :raise HTTPException:
    """
    lock_owner_token:Optional[str] = None
    async with database.with_get_db() as session:
        # try to lock event
        event_db, lock_owner_token = await read_event_one_wrapper(session, event_db_id)

        try:
            # try to create channel
            event_db = await _create_channel(session, member, event_db, lock_owner_token)
            
            # join channel
            await _join_channel(session, member, event_db, lock_owner_token)
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.error(f"fail to join Event (id={event_db_id}): {str(e)}")
            raise HTTPException(500, f"fail to join Event (id={event_db_id})")
        finally:
            try:
                await crud.unlock_event(session, event_db_id, lock_owner_token)
            except Exception as e:
                logger.critical(f"fail to unlock Event (id={event_db_id}): {str(e)}")
    
    return


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
    guild = get_guild()
    
    # get archive category
    if (archive_category := get_category.get_category(guild, settings.ARCHIVE_CATEGORY_ID)) is None:
        logger.critical(f"Archive Category (id={settings.ARCHIVE_CATEGORY_ID}) not found")
        raise HTTPException(500, f"Archive Category (id={settings.ARCHIVE_CATEGORY_ID}) not found")
    
    async with database.with_get_db() as session:
        event_db, lock_owner_token = await read_event_one_wrapper(session, event_db_id)
        try:
            async with session.begin():
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
            
            # logging
            logger.info(f"Event {event_db_returning["title"]} (id={event_db_returning["id"]}) was archived: {reason}")
            
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
            try:
                await crud.unlock_event(session, event_db_id, lock_owner_token)
            except Exception as e:
                logger.critical(f"fail to unlock Event (id={event_db_id}): {str(e)}")
    
    return


async def link_event_to_channel(event_db_id:int, channel_id:int):
    """
    Link the Event to the channel.
    
    :param event_db_id:
    :param channel_id: The channel which the Event will be linked to.
    
    :raise HTTPException:
    """
    lock_owner_token = None
    
    # get guild
    guild = get_guild()
    
    # get channel
    if (channel := guild.get_channel(channel_id)) is None or \
            not isinstance(channel, discord.TextChannel):
        raise HTTPException(400, f"Channel (id={channel_id}) not found")
    
    async with database.with_get_db() as session:
        event_db, lock_owner_token = await read_event_one_wrapper(session, event_db_id)
        try:
            async with session.begin():
                # update database
                event_db:model.Event = await crud.update_event(
                    session=session,
                    id=event_db.id,
                    lock_owner_token=lock_owner_token,
                    channel_id=channel.id
                )
        except IntegrityError:
            raise HTTPException(400, f"Channel (id={channel_id}) has been linked to other Event")
        except Exception as e:
            logger.error(f"fail to link Event (id={event_db_id}) to channel (id={channel_id}): {str(e)}")
            raise HTTPException(500, f"fail to link Event (id={event_db_id}) to channel (id={channel_id})")
        finally:
            try:
                await crud.unlock_event(session, event_db_id, lock_owner_token)
            except Exception as e:
                logger.critical(f"fail to unlock Event (id={event_db_id}): {str(e)}")
    
    # logging
    logger.info(f"Event (id={event_db_id}) was linked to channel (id={channel_id}) successfully")
    
    return


async def create_custom_event(title:str):
    """
    Create a custom Event.
    
    :param title:
    
    :raise HTTPException:
    """
    # get guild
    guild = get_guild()
    
    # create the custom event in database
    event_db_id = None
    try:
        async with database.with_get_db() as session:
            async with session.begin():
                event_db = await crud.create_event(session, title=title)
            event_db_id = event_db.id
    except Exception as e:
        logger.error(f"fail to create a custom event: {str(e)}")
        raise HTTPException(500, f"fail to create a custom event")
    
    # send notification
    embed = discord.Embed(color=discord.Color.green(), title=f"Click the button to join {title}")
    embed.set_footer(text=f"ID: {event_db_id}")
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