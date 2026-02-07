import logging

from discord.ext import commands, tasks
import discord

from src.backend import security
from src.backend import channel_op
from src.config import settings
from src import bgtask

# logging
logger = logging.getLogger("uvicorn")

# cog
class CTFBGTask(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
    
    
    @commands.Cog.listener()
    async def on_ready(self):
        # start background task
        if not self.task_checks.is_running():
            self.task_checks.start()
    
    # background task
    @tasks.loop(minutes=settings.CHECK_INTERVAL_MINUTES)
    async def task_checks(self):
        # process
        await bgtask._detect_events_new()
        await bgtask._detect_event_update_and_remove()
        await bgtask._auto_archive()
        await bgtask._recover_scheduled_events()
    
    
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
        
        if (custom_id := interaction.data.get("custom_id", None)) is None:
            return
        
        if custom_id.startswith("ctf_join_channel:"):
            # check user
            if (member := await security.discord_check_user_and_auto_register(interaction, False)) is None:
                return
            
            # get event db id
            try:
                event_db_id:int = int(custom_id.split(":")[1])
            except Exception:
                await interaction.response.send_message("Invalid arguments", ephemeral=True)
                return
            
            # join channel
            await interaction.response.defer(ephemeral=True)
            try:
                await channel_op.create_and_join_channel(member, event_db_id)
            except Exception as e:
                await interaction.followup.send(str(e), ephemeral=True)
                return
            
            await interaction.followup.send("Done", ephemeral=True)
            return
        

def setup(bot:commands.Bot):
    bot.add_cog(CTFBGTask(bot))