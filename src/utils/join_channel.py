from typing import Optional
import logging

from discord.ext import commands
import discord

from src.database.model import Event
from src.database.database import get_db
from src import crud
from src.utils.ctf_api import fetch_ctf_events
from src.utils.embed_creator import create_event_embed

logger = logging.getLogger(__name__)

async def join_channel(
    bot:commands.Bot,
    interaction:discord.Interaction,
    event_id:int,
):
    await interaction.response.defer(ephemeral=True)
        
    async with get_db() as session:
        # get event from database
        events = await crud.read_event(session, event_id=[event_id])
        if len(events) != 1:
            await interaction.followup.send(content="Invalid event", ephemeral=True)
            return
        event:Event = events[0]
        
        if not(event.channel_id is None) and not(bot.get_channel(event.channel_id) is None): # channel exists
            try:
                member = interaction.guild.get_member(interaction.user.id)
                channel = bot.get_channel(event.channel_id)
                
                if channel.permissions_for(member).view_channel == True:
                    await interaction.followup.send(content="You have joined the channel", ephemeral=True)
                    return
                
                await channel.set_permissions(member, view_channel=True)
                await channel.send(embed=discord.Embed(
                    color=discord.Color.green(),
                    title=f"{interaction.user.display_name} joined the channel"
                ))
                
                await interaction.followup.send(content="Done", ephemeral=True)
                
                logger.info(f"User {interaction.user.display_name}(id={interaction.user.id}) joined channel {channel.name}(id={channel.id})")
                return
            except Exception as e:
                logger.error(f"Failed to join channel: {e}")
                await interaction.followup.send(content=f"Failed to join channel: {e}", ephemeral=True)
                return
        else: # channel not found or invalid
            # get event from CTFTime
            events_api = await fetch_ctf_events(event.event_id)
            if len(events_api) != 1:
                await interaction.followup.send(content="Invalid event", ephemeral=True)
                return
            event_api:Event = events_api[0]
            
            # create channel
            category_name = "Incoming/Running CTF"
            guild = interaction.guild
            category = discord.utils.get(interaction.guild.categories, name=category_name)
            if category is None:
                await interaction.followup.send(content=f"Category '{category_name}' not found.", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True),
                guild.me: discord.PermissionOverwrite(view_channel=True)
            }

            try:
                new_channel = await guild.create_text_channel(event.title, category=category, overwrites=overwrites)
                event_id = event.event_id
                event = await crud.update_event(session, event_id=event_id, channel_id=new_channel.id)
                if event is None:
                    await new_channel.delete(reason=f"Failed to update event_id={event_id} on database")
                    await interaction.followup.send(content=f"Failed to create channel: Failed to update event_id={event_id} on database", ephemeral=True)
                    return
                
                embed = await create_event_embed(event_api, f"{interaction.user.display_name} 發起了 {event.title}")
                
                await new_channel.send(embed=embed)
                    
                await interaction.followup.send(content="Done", ephemeral=True)
                
                logger.info(f"User {interaction.user.display_name}(id={interaction.user.id}) created and joined channel {new_channel.name}(id={new_channel.id})")
                return
            except Exception as e:
                logger.error(f"Failed to create channel: {e}")
                await interaction.followup.send(content=f"Failed to create channel: {e}", ephemeral=True)
                return
            

async def join_channel_custom(
    bot:commands.Bot,
    interaction:discord.Interaction,
    channel_id:int,
):
    await interaction.response.defer(ephemeral=True)
    
    # get channel from database
    async with get_db() as session:
        channel_db = await crud.read_custom_channel(session, channel_id=channel_id)
    if len(channel_db) != 1:
        await interaction.followup.send(f"Channel (id={channel_id}) not found", ephemeral=True)
        return
    
    # get channel from discord
    channel = bot.get_channel(channel_id)
    if channel is None:
        await interaction.followup.send(f"Channel (id={channel_id}) not found", ephemeral=True)
        return
    
    # join channel
    try:
        if channel.permissions_for(interaction.user).view_channel == True:
            await interaction.followup.send(content="You have joined the channel", ephemeral=True)
            return
                
        await channel.set_permissions(interaction.user, view_channel=True)
        await channel.send(embed=discord.Embed(
            color=discord.Color.green(),
            title=f"{interaction.user.display_name} joined the channel"
        ))
                
        await interaction.followup.send(content="Done", ephemeral=True)
                
        logger.info(f"User {interaction.user.display_name}(id={interaction.user.id}) joined channel {channel.name}(id={channel.id})")
        return
    except Exception as e:
        logger.error(f"Failed to join channel: {e}")
        await interaction.followup.send(content=f"Failed to join channel: {e}", ephemeral=True)
        return
