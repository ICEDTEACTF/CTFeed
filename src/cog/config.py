from enum import Enum
import logging

from pydantic import BaseModel
from discord.ext import commands
import discord

from src.database import model
from src.backend import security
from src.backend import config

# logging
logger = logging.getLogger("uvicorn")

# view
class ConfigMenu(discord.ui.View):
    def __init__(self, bot:commands.Bot):
        super().__init__(timeout=None)
        
        self.bot = bot
        self.state = "MAIN"
        
    
    async def build_embed_and_view(self) -> discord.Embed:
        # build embed
        try:
            config_info = await config.read_config(self.bot, self.state if self.state != "MAIN" else None)
        except Exception as e:
            return discord.Embed(title=f"Fail to read config", description=str(e), color=discord.Color.red())
        
        color = discord.Color.green()
        for c in config_info.config:
            if not c.ok:
                color = discord.Color.red()
        
        embed = discord.Embed(color=color)
        if self.state == "MAIN":
            embed.title = "Configuration"
            for c in config_info.config:
                embed.add_field(name=c.key, value=c.message, inline=False)
        else:
            c = config_info.config[0]
            embed.title = c.key
            embed.description = c.description
            embed.add_field(name="Value", value=c.message, inline=False)
            
        embed.set_footer(text=f"Guild info: {config_info.guild_name} (id={config_info.guild_id})")
        
        # build view
        await self._build_view()
        
        return embed


    async def _build_view(self):
        self.clear_items()
        
        self.change_page = discord.ui.Select(
            placeholder="Details",
            min_values=1,
            max_values=1,
            row=1,
            options=[discord.SelectOption(label="MAIN")] + \
                [discord.SelectOption(label=k) for k in model.config_info]
        )
        self.change_page.callback = self.on_change_page
        self.add_item(self.change_page)
        
        if self.state != "MAIN":
            config_info = model.config_info[self.state]
            self.edit = discord.ui.Select(
                placeholder="Edit",
                min_values=1,
                max_values=1,
                row=2,
                select_type=config_info.select_type
            )
            self.edit.callback = self.on_edit
            self.add_item(self.edit)
        
        return


    async def on_change_page(self, interaction:discord.Interaction):
        # check permission
        if not(await security.discord_check_administrator(interaction)):
            return
        
        # check argument
        try:
            state = str(self.change_page.values[0])
        except Exception:
            await interaction.response.send_message("Invalid arguments", ephemeral=True)
            return

        # change state
        key = "MAIN" if state == "MAIN" else None
        
        if key is None:
            for k in model.config_info:
                if state == k:
                    key = k
                    break
                
        if key is None:
            await interaction.response.send_message("Invalid arguments", ephemeral=True)
            return
        
        # return
        self.state = key
        embed = await self.build_embed_and_view()
        await interaction.response.edit_message(embed=embed, view=self)
        return


    async def on_edit(self, interaction:discord.Interaction):
        # check permission
        if not (await security.discord_check_administrator(interaction)):
            return

        # check argument
        try:
            value = self.edit.values[0].id
        except Exception as e:
            await interaction.response.send_message("Invalid arguments", ephemeral=True)
            return
        
        # update
        try:
            await config.update_config(self.bot, (self.state, value))
        except Exception as e:
            await interaction.response.send_message(f"fail to update config (key={self.state}): {str(e)}", ephemeral=True)
            return
        
        # logging
        logger.info(f"User {interaction.user.name} (id={interaction.user.id}) updated Config (key={self.state}) to value={value}")
        
        # return
        embed = await self.build_embed_and_view()
        await interaction.response.edit_message(embed=embed, view=self)
        return


class Config(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
    
    
    @discord.slash_command(name="config", description="Config Panel")
    async def config_menu(self, ctx:discord.ApplicationContext):
        # check permission
        if not (await security.discord_check_administrator(ctx)):
            return
        
        view = ConfigMenu(self.bot)
        embed = await view.build_embed_and_view()
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)
        return
        

def setup(bot:commands.Bot):
    bot.add_cog(Config(bot))
