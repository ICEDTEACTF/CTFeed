from typing import List
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

import discord
from discord.ext import commands

from src.config import settings
from src.database.database import get_db
from src.database.model import Event, CustomChannel
from src import crud
from src.utils.join_channel import join_channel, join_channel_custom

# logging
logger = logging.getLogger(__name__)

# misc
async def show_custom_channels(bot:commands.Bot) -> discord.Embed:
    async with get_db() as session:
        custom_channels:List[CustomChannel] = await crud.read_custom_channel(session)
        
    # embed
    embed = discord.Embed(
        title=f"{settings.EMOJI} Custom CTF channels",
        color=discord.Color.green()
    )
    for channel in custom_channels:
        discord_channel = bot.get_channel(channel.channel_id)
        if discord_channel is None:
            continue
            
        embed.add_field(
            name=f"{discord_channel.name}",
            value=f"id = {discord_channel.id}",
            inline=False
        )
    
    return embed


# ui - ctf menu
class CTFMenuView(discord.ui.View):
    def __init__(self, bot:commands.Bot):
        super().__init__(timeout=None)
        
        self.bot = bot

    
    @discord.ui.button(label="Join a channel", custom_id="ctf_select_channel", style=discord.ButtonStyle.blurple, emoji=settings.EMOJI)
    async def ctf_select_channel_callback(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.send_modal(JoinChannelModal(bot=self.bot, title="Create / Join channel via CTFTime event id"))
        
    
    @discord.ui.button(label="Custom channels", custom_id="ctf_view_custom_channel", style=discord.ButtonStyle.gray)
    async def ctf_view_custom_channel(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        embed = await show_custom_channels(self.bot)
        await interaction.followup.send(embed=embed, view=CustomChannelView(self.bot), ephemeral=True)


class JoinChannelModal(discord.ui.Modal):
    def __init__(self, bot:commands.Bot, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
        self.bot = bot
        
        self.add_item(discord.ui.InputText(label="Enter CTFTime event id", style=discord.InputTextStyle.short))


    async def callback(self, interaction: discord.Interaction):
        try:
            event_id = int(self.children[0].value)
        except:
            await interaction.response.send_message(content="Invalid arguments", ephemeral=True)
            return
            
        await join_channel(self.bot, interaction, event_id)
        return
    

# ui - custom channel menu
class CustomChannelView(discord.ui.View):
    def __init__(self, bot:commands.Bot):
        super().__init__(timeout=None)
        
        self.bot = bot

    @discord.ui.button(label="Create a custom channel", custom_id="ctf_create_custom_channel", style=discord.ButtonStyle.success)
    async def ctf_create_custom_channel(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.send_modal(CreateCustomChannelModal(bot=self.bot, title="Create custom channel"))
        
    
    @discord.ui.button(label="Join a custom channel", custom_id="ctf_join_custom_channel", style=discord.ButtonStyle.blurple)
    async def ctf_join_custom_channel(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.send_modal(JoinCustomChannelModal(bot=self.bot, title="Join custom channel"))


class CreateCustomChannelModal(discord.ui.Modal):
    def __init__(self, bot:commands.Bot, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
        self.bot = bot
        
        self.add_item(discord.ui.InputText(label="Channel name", style=discord.InputTextStyle.short))


    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        channel_name = self.children[0].value
    
        # find category
        category_name = "Incoming/Running CTF"
        guild = interaction.guild
        category = discord.utils.get(interaction.guild.categories, name=category_name)
        if category is None:
            await interaction.followup.send(content=f"Category '{category_name}' not found.", ephemeral=True)
            return
    
        # create channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }
        
        async with get_db() as session:
            try:
                channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
                channel_db = await crud.create_custom_channel(session, channel_id=channel.id)
                if channel_db is None:
                    reason = f"Failed to create CustomChannel (channel_id={channel.id}) on database"
                    await channel.delete(reason=reason)
                    await interaction.followup.send(content=f"Failed to create custom channel: {reason}", ephemeral=True)
                    return

                # send announcement
                view = discord.ui.View(timeout=None)
                view.add_item(
                    discord.ui.Button(
                        label='Join',
                        style=discord.ButtonStyle.blurple,
                        custom_id=f'ctf_join_channel:custom:{channel.id}',
                        emoji=settings.EMOJI,
                    )
                )
                
                await interaction.channel.send(
                    embed=discord.Embed(
                        color=discord.Color.green(),
                        title=f"Click the button to join channel {channel.name}"
                    ),
                    view=view,
                )
                
                # send welcome messahe
                await channel.send(embed=discord.Embed(
                    color=discord.Color.green(),
                    title=f"{interaction.user.display_name} created the channel"
                ))
                
                # update
                embed = await show_custom_channels(self.bot)
                await interaction.followup.send(embed=embed, view=CustomChannelView(self.bot), ephemeral=True)

                logger.info(f"User {interaction.user.display_name}(id={interaction.user.id}) created and joined channel {channel.name}(id={channel.id})")
                return
            except Exception as e:
                logger.error(f"Failed to create channel: {e}")
                await interaction.followup.send(content=f"Failed to create channel: {e}", ephemeral=True)
                return


class JoinCustomChannelModal(discord.ui.Modal):
    def __init__(self, bot:commands.Bot, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
        self.bot = bot
        
        self.add_item(discord.ui.InputText(label="Channel ID", style=discord.InputTextStyle.short))
    
    
    async def callback(self, interaction:discord.Interaction):
        try:
            channel_id = int(self.children[0].value)
        except:
            await interaction.response.send_message("Invalid arguments", ephemeral=True)
            return
        
        await join_channel_custom(self.bot, interaction, channel_id)
        return


# cog
class CTF(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
    
    
    @discord.slash_command(name="ctf_menu", description="list CTF events")
    async def ctf_menu(self, ctx:discord.ApplicationContext):
        async with get_db() as session:
            known_events:List[Event] = await crud.read_event(session)
        
        # embed
        embed = discord.Embed(
            title=f"{settings.EMOJI} CTF events tracked",
            color=discord.Color.green()
        )
        for event in known_events:
            embed.add_field(
                name=f"[id={event.event_id}] {event.title}",
                value=f"start at {datetime.fromtimestamp(event.start).astimezone(ZoneInfo(settings.TIMEZONE))}\n\
                finish at {datetime.fromtimestamp(event.finish).astimezone(ZoneInfo(settings.TIMEZONE))}",
                inline=False
            )
        
        await ctx.response.send_message(embed=embed, view=CTFMenuView(self.bot), ephemeral=True)


def setup(bot:commands.Bot):
    bot.add_cog(CTF(bot))
