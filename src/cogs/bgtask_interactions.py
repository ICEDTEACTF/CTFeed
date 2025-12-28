from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

import discord
from discord.ext import commands, tasks

from src.config import settings
from src.database.database import get_db
from src.database.model import Event
from src.utils.ctf_api import fetch_ctf_events
from src.utils.embed_creator import create_event_embed
from src.utils.join_channel import join_channel, join_channel_custom
from src import crud

# logging
logger = logging.getLogger(__name__)
    
# utils
async def get_announcement_channel(bot:commands.Bot) -> discord.TextChannel:
    channel_name = settings.ANNOUNCEMENT_CHANNEL_NAME
    
    channel = None
    for guild in bot.guilds:
        for text_channel in guild.text_channels:
            if text_channel.name.lower() == channel_name.lower():
                channel = text_channel
                break
        if channel:
            break

    if not channel:
        logger.error(f"Can't find channel named '{channel_name}'")
        logger.error(f"Please check:")
        logger.error(f"1. Channel name is correct: {channel_name}")
        logger.error(f"2. Bot has permission to view the channel")
        logger.error(f"3. The channel exists in the server where the Bot is located")
        await bot.close()
        return
    
    return channel


# cog
class CTFBGTask(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        # start background task
        self.task_checks.start()
        
    # background task
    @tasks.loop(minutes=settings.CHECK_INTERVAL_MINUTES)
    async def task_checks(self):
        # get channel
        channel:discord.TextChannel = await get_announcement_channel(self.bot)
        
        # 1. get new events
        async with get_db() as session:
            all_events = await fetch_ctf_events()
            
            known_events = await crud.read_event(
                session,
                finish_after=(datetime.now() + timedelta(days=settings.DATABASE_SEARCH_DAYS)).timestamp()
            ) # get all known events with finish after now+DATABASE_SEARCH_DAYS (for example now+(-90))
            known_events_id = [ event.event_id for event in known_events ]
        
            new_events_db:List[Event] = [] # new events data for database
            new_events_ctftime:List[Dict[str, Any]] = [] # new events data from CTFTime
            for event in all_events:
                event_id = event["id"]
                if event_id not in known_events_id: # new event
                    new_events_db.append(Event(
                        event_id=event_id,
                        title=event["title"],
                        start=datetime.fromisoformat(event["start"]).timestamp(),
                        finish=datetime.fromisoformat(event["finish"]).timestamp(),
                    ))
                    
                    new_events_ctftime.append(event)
                    
            if len(new_events_db) > 0:
                await crud.create_event(session, new_events_db)
            
            for event in new_events_ctftime:
                embed = await create_event_embed(event, "有新的 CTF 競賽！")
                
                view = discord.ui.View(timeout=None)
                view.add_item(
                    discord.ui.Button(
                        label='Join',
                        style=discord.ButtonStyle.blurple,
                        custom_id=f'ctf_join_channel:event:{event_id}',
                        emoji=settings.EMOJI,
                    )
                )
                try:
                    await channel.send(embed=embed, view=view)
                    logger.info(f"Sent new event notification: {event['title']}")
                except Exception as e:
                    logger.error(f"Failed to send notification: {e}")
            
        # 2. detect updates
        # - event updates
        # - event removed
        # - custom channel removed
        known_events.extend(new_events_db)
        async with get_db() as session:
            # check events
            for event in known_events:
                events_api = await fetch_ctf_events(event.event_id)
                if len(events_api) != 1:
                    # event removed
                    logger.info(f"Detected: {event.title} (event_id={event.event_id}) was removed")
                    
                    await crud.delete_event(session, event_id=[event.event_id])
                    
                    embed = discord.Embed(
                        color=discord.Color.red(),
                        title=f"{event.title} was removed",
                        footer=discord.EmbedFooter(text=f"Event ID: {event.event_id} | CTFtime.org")
                    )
                    # send notification to announcement channel
                    await channel.send(embed=embed)
                    # send notification to private channel
                    if not(event.channel_id is None) and not(self.bot.get_channel(event.channel_id) is None):
                        await self.bot.get_channel(event.channel_id).send(embed=embed)
                else: 
                    # check update
                    event_api = events_api[0]
                    ntitle = event_api["title"]
                    nstart = datetime.fromisoformat(event_api["start"]).timestamp()
                    nfinish = datetime.fromisoformat(event_api["finish"]).timestamp()
                    
                    if event.title != ntitle or \
                        event.start != nstart or event.finish != nfinish:
                        # update detected
                        logger.info(f"Detected: {ntitle} (old: {event.title}) (event_id={event.event_id}) was updated")
                        
                        await crud.update_event(session, event_id=event.event_id,
                                          title=ntitle,
                                          start=nstart,
                                          finish=nfinish)
                        
                        embed = await create_event_embed(event_api, title="Update detected")
                        # send notification to announcement channel
                        await channel.send(embed=embed)
                        # send notification to private channel
                        if not(event.channel_id is None) and not(self.bot.get_channel(event.channel_id) is None):
                            await self.bot.get_channel(event.channel_id).send(embed=embed)
            
            
            # check custom channels
            custom_channels = await crud.read_custom_channel(session)
            for channel_db in custom_channels:
                channel = self.bot.get_channel(channel_db.channel_id)
                if channel is None: # custom channel removed
                    logger.info(f"Detected: custom channel id={channel_db.channel_id} was removed")
                    await crud.delete_custom_channel(session, channel_db.channel_id)
    
        
    @task_checks.before_loop
    async def before_task_checks(self):
        await self.bot.wait_until_ready()


    def cog_unload(self):
        self.task_checks.cancel()
    

    # interaction handler
    @commands.Cog.listener()
    async def on_interaction(self, interaction:discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id")
        if custom_id is None:
            return
        
        if custom_id.startswith("ctf_join_channel:event:"):
            try:
                _ = custom_id.split(":")
                event_id:int = int(_[2])
            except:
                await interaction.response.send_message("Invalid arguments", ephemeral=True)
                return
            
            await join_channel(self.bot, interaction, event_id)
        elif custom_id.startswith("ctf_join_channel:custom:"):
            try:
                _ = custom_id.split(":")
                channel_id:int = int(_[2])
            except:
                await interaction.response.send_message("Invalid arguments", ephemeral=True)
                return
            
            await join_channel_custom(self.bot, interaction, channel_id)
    
        return
    

def setup(bot:commands.Bot):
    bot.add_cog(CTFBGTask(bot))
