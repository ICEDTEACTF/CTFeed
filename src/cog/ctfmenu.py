from datetime import datetime, timezone
from typing import Literal, Optional, List
import logging
import math

from fastapi import HTTPException
from discord.ext import commands
import discord

from src.backend import security
from src.backend import channel_op
from src.database import database
from src.database import model
from src.config import settings
from src import crud

# logging
logger = logging.getLogger("uvicorn")

# utils
def _format_channel_info(guild: Optional[discord.Guild], channel_id: Optional[int]) -> str:
    if channel_id is None:
        return "(Not linked)"
    if guild is None:
        return f"<#{channel_id}>"
    if guild.get_channel(channel_id) is None:
        return f"(Invalid) <#{channel_id}>"
    return f"<#{channel_id}>"


# views
class EventMenu(discord.ui.View):
    def __init__(self, bot: commands.Bot, owner_id: int, type: Literal["ctftime", "custom"]):
        super().__init__(timeout=None)
        self.bot = bot
        self.owner_id = owner_id
        self.type = type
        self.page = 0
        self.per_page = 5
        self.events: List[model.Event] = []


    async def _check_permission(self, interaction: discord.Interaction) -> Optional[discord.Member]:
        if (member := (await security.discord_check_user_and_auto_register(interaction, False))) is None:
            return None
        if member.id != self.owner_id:
            await interaction.response.send_message("You are not the owner of this view", ephemeral=True)
            return None
        return member


    async def _refresh_view(self, total_pages: int):
        self.prev_page.disabled = self.page <= 0
        self.next_page.disabled = self.page >= total_pages - 1

        start = self.page * self.per_page
        end = start + self.per_page
        current = self.events[start:end]

        self.select_event.disabled = len(current) == 0
        if len(current) == 0:
            self.select_event.options = [discord.SelectOption(label="(None)", value="none")]
        else:
            self.select_event.options = [
                discord.SelectOption(
                    label=e.title[:80],
                    value=str(e.id),
                    description=(
                        f"CTFTime ID: {e.event_id}" if self.type == "ctftime" else f"DB ID: {e.id}"
                    )[:100]
                )
                for e in current
            ]

        self.switch_menu.label = "Custom Events" if self.type == "ctftime" else "CTFTime Events"

        if self.type == "custom":
            if self.create_custom_event not in self.children:
                self.add_item(self.create_custom_event)
        else:
            if self.create_custom_event in self.children:
                self.remove_item(self.create_custom_event)


    async def build_embed_and_view(self) -> discord.Embed:
        try:
            async with database.with_get_db() as session:
                self.events = await crud.read_event(
                    session=session,
                    type=self.type,
                    archived=False
                )
        except Exception as e:
            logger.error(f"fail to read Events: {str(e)}")
            return discord.Embed(title="Fail to read events", color=discord.Color.red())

        if self.type == "custom":
            self.events = sorted(self.events, key=lambda e: e.id)

        total_pages = max(1, math.ceil(len(self.events) / self.per_page))
        if self.page >= total_pages:
            self.page = total_pages - 1
        if self.page < 0:
            self.page = 0

        start = self.page * self.per_page
        end = start + self.per_page
        current = self.events[start:end]

        title = "CTFTime Events" if self.type == "ctftime" else "Custom Events"
        if len(current) == 0:
            description = "(No events)"
        else:
            lines = []
            for idx, e in enumerate(current, start=start + 1):
                channel_created = "[⭐️ Channel created]" if e.channel_id is not None else ""
                
                if self.type == "ctftime":
                    time_now = int(datetime.now(timezone.utc).timestamp())
                    now_running = "[🏃 Now running]" if e.start <= time_now and time_now <= e.finish else ""
                    
                    lines.append(f"**[ID: {e.id} | CTFTime: {e.event_id}] {e.title}**")
                    if (len(channel_created) + len(now_running)) != 0:
                        lines.append(f"{channel_created}{now_running}")
                    lines.append(f"Start: <t:{e.start}:F> (<t:{e.start}:R>)")
                    lines.append(f"End: <t:{e.finish}:F> (<t:{e.finish}:R>)")
                    lines.append(f"")
                else:
                    lines.append(f"**[ID: {e.id}] {e.title}**")
                    if len(channel_created) != 0:
                        lines.append(f"{channel_created}")
                    lines.append("")
            description = "\n".join(lines)

        embed = discord.Embed(title=title, description=description, color=discord.Color.green())
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages} | Total {len(self.events)}")

        await self._refresh_view(total_pages)
        return embed


    @discord.ui.button(style=discord.ButtonStyle.grey, label="Previous", row=0)
    async def prev_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        if await self._check_permission(interaction) is None:
            return
        self.page -= 1
        embed = await self.build_embed_and_view()
        await interaction.response.edit_message(embed=embed, view=self)


    @discord.ui.button(style=discord.ButtonStyle.grey, label="Next", row=0)
    async def next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        if await self._check_permission(interaction) is None:
            return
        self.page += 1
        embed = await self.build_embed_and_view()
        await interaction.response.edit_message(embed=embed, view=self)


    @discord.ui.select(
        placeholder="Select event...",
        disabled=True,
        min_values=1,
        max_values=1,
        options=[discord.SelectOption(label="dummy")],
        row=1
    )
    async def select_event(self, select: discord.ui.Select, interaction: discord.Interaction):
        if await self._check_permission(interaction) is None:
            return
        if select.values[0] == "none":
            await interaction.response.send_message("No event", ephemeral=True)
            return
        try:
            event_db_id = int(select.values[0])
        except Exception:
            await interaction.response.send_message("Invalid selection", ephemeral=True)
            return

        detail_view = EventDetailMenu(self.bot, self.owner_id, event_db_id, self.type)
        embed = await detail_view.build_embed_and_view()
        await interaction.response.send_message(embed=embed, view=detail_view, ephemeral=True)


    @discord.ui.button(style=discord.ButtonStyle.blurple, label="Custom Events", row=2)
    async def switch_menu(self, button: discord.ui.Button, interaction: discord.Interaction):
        if await self._check_permission(interaction) is None:
            return
        target_type = "custom" if self.type == "ctftime" else "ctftime"
        target_view = EventMenu(self.bot, self.owner_id, target_type)
        embed = await target_view.build_embed_and_view()
        await interaction.response.edit_message(embed=embed, view=target_view)


    @discord.ui.button(style=discord.ButtonStyle.green, label="Create Custom Event", row=2)
    async def create_custom_event(self, button: discord.ui.Button, interaction: discord.Interaction):
        if await self._check_permission(interaction) is None:
            return
        if self.type != "custom":
            await interaction.response.send_message("Switch to Custom Events first", ephemeral=True)
            return
        
        await interaction.response.send_modal(CreateCustomEventModal(title="Create custom event"))
        return


class EventDetailMenu(discord.ui.View):
    def __init__(self, bot: commands.Bot, owner_id: int, event_db_id: int, type: Literal["ctftime", "custom"]):
        super().__init__(timeout=None)
        self.bot = bot
        self.owner_id = owner_id
        self.event_db_id = event_db_id
        self.type = type


    async def _check_permission(self, interaction: discord.Interaction, force_pm:bool) -> Optional[discord.Member]:
        if (member := (await security.discord_check_user_and_auto_register(interaction, force_pm))) is None:
            return None
        if member.id != self.owner_id:
            await interaction.response.send_message("You are not the owner of this view", ephemeral=True)
            return None
        return member


    async def _read_event(self) -> Optional[model.Event]:
        try:
            async with database.with_get_db() as session:
                events = await crud.read_event(
                    session=session,
                    type=self.type,
                    archived=False,
                    id=self.event_db_id
                )
                if len(events) != 1:
                    return None
                return events[0]
        except Exception as e:
            logger.error(f"fail to read Event (id={self.event_db_id}): {str(e)}")
            return None


    async def build_embed_and_view(self) -> discord.Embed:
        # read event
        event = await self._read_event()
        if event is None:
            self.clear_items()
            return discord.Embed(title="Event not found", color=discord.Color.red())

        # build embed
        guild = self.bot.get_guild(settings.GUILD_ID)
        channel_info = _format_channel_info(guild, event.channel_id)
        users_count = len(event.users)

        embed = discord.Embed(title=event.title, color=discord.Color.green())
        embed.add_field(name="Database ID", value=str(event.id), inline=True)

        if self.type == "ctftime":
            embed.add_field(name="CTFTime ID", value=str(event.event_id), inline=True)
            embed.add_field(name="Start", value=f"<t:{event.start}:F> (<t:{event.start}:R>)", inline=False)
            embed.add_field(name="Finish", value=f"<t:{event.finish}:F> (<t:{event.finish}:R>)", inline=False)

        embed.add_field(name="Channel", value=channel_info, inline=False)
        embed.add_field(name="Participants", value=str(users_count), inline=True)
        embed.set_footer(text="CTFTime Event" if self.type == "ctftime" else "Custom Event")

        # build view
        pm_member = None
        try:
            pm_member = await security.check_user(self.owner_id, True)
        except Exception:
            pass
        if pm_member:
            if self.relink_channel not in self.children:
                self.add_item(self.relink_channel)
            if self.archive_event not in self.children:
                self.add_item(self.archive_event)
        else:
            if self.relink_channel in self.children:
                self.remove_item(self.relink_channel)
            if self.archive_event in self.children:
                self.remove_item(self.archive_event)

        return embed


    @discord.ui.button(style=discord.ButtonStyle.green, label="Join", row=0)
    async def join_event(self, button: discord.ui.Button, interaction: discord.Interaction):
        # check permission
        if (member := (await self._check_permission(interaction, False))) is None:
            return
        
        # create or join channel
        try:
            await channel_op.create_and_join_channel(member, self.event_db_id)
        except HTTPException as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        except Exception as e:
            logger.error(f"fail to join Event (id={self.event_db_id}): {str(e)}")
            await interaction.response.send_message("fail to join Event", ephemeral=True)
            return

        embed = await self.build_embed_and_view()
        await interaction.response.edit_message(embed=embed, view=self)


    @discord.ui.button(style=discord.ButtonStyle.red, label="Archive Event", row=0)
    async def archive_event(self, button: discord.ui.Button, interaction: discord.Interaction):
        # check permission
        if (member := await self._check_permission(interaction, True)) is None:
            return
        
        # archive event
        try:
            await channel_op.archive_event(self.event_db_id, f"Manually archived by {member.name} (id={member.id})")
        except HTTPException as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        except Exception as e:
            logger.error(f"fail to archive Event (id={self.event_db_id}): {str(e)}")
            await interaction.response.send_message(f"fail to archive Event (id={self.event_db_id})", ephemeral=True)
            return
        
        await interaction.response.edit_message(embed=discord.Embed(
            color=discord.Color.green(),
            title=f"Event (id={self.event_db_id}) was archived successfully"
        ), view=None)
        return
    
    
    @discord.ui.select(
        select_type=discord.ComponentType.channel_select,
        placeholder="Link a channel to the Event...",
        min_values=1,
        max_values=1,
        row=1
    )
    async def relink_channel(self, select: discord.ui.Select, interaction: discord.Interaction):
        # check permission
        if await self._check_permission(interaction, True) is None:
            return
        
        # argument check
        try:
            channel = select.values[0]
        except Exception:
            await interaction.response.send_message("Invalid selection", ephemeral=True)
            return

        # relink
        try:
            await channel_op.link_event_to_channel(self.event_db_id, channel.id)
        except HTTPException as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        except Exception as e:
            logger.error(f"fail to link channel (id={channel.id}) to Event (id={self.event_db_id}): {str(e)}")
            await interaction.response.send_message(f"fail to link channel (id={channel.id}) to Event (id={self.event_db_id})", ephemeral=True)
            return
        
        # response
        embed = await self.build_embed_and_view()
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        return


class CreateCustomEventModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
        self.add_item(discord.ui.InputText(label="Event title", style=discord.InputTextStyle.short))


    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        title = self.children[0].value
        
        try:
            await channel_op.create_custom_event(title)
        except Exception as e:
            await interaction.followup.send(content=str(e), ephemeral=True)
        
        await interaction.followup.send(content="Done", ephemeral=True)


# cog
class CTFMenu(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @discord.slash_command(name="ctfmenu", description="CTFTime Event Menu")
    async def ctfmenu(self, ctx: discord.ApplicationContext):
        if (member := (await security.discord_check_user_and_auto_register(ctx, False))) is None:
            return

        view = EventMenu(self.bot, member.id, "ctftime")
        embed = await view.build_embed_and_view()
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(CTFMenu(bot))
