import logging

from discord.ext import commands
import discord

from src.backend import security
from src.backend import user
from src.database import database
from src.database import model
from src import crud
from src import schema
from src.config import settings

# logging
logger = logging.getLogger("uvicorn")

# view
class UserMenu(discord.ui.View):
    def __init__(self, bot:commands.Bot, discord_id:int):
        super().__init__(timeout=None)
        
        self.bot = bot
        self.discord_id = discord_id
    
    
    async def build_embed_and_view(self) -> discord.Embed:
        async with database.with_get_db() as session:
            try:
                users_s = await user.get_user(session, self.discord_id)
            except Exception as e:
                return discord.Embed(title="Fail to read User", color=discord.Color.red())
        user_s = users_s[0]
        
        # build embed
        color = discord.Color.green() if user_s.status == model.Status.online else discord.Color.red()
        
        if user_s.discord is not None:
            embed = discord.Embed(
                title=f"{user_s.discord.display_name}",
                description=f"Name: {user_s.discord.name}\nID: {user_s.discord.id}",
                color=color
            )
        else:
            embed = discord.Embed(
                title=f"(Invalid)",
                description=f"Name: (Invalid)\nID: {user_s.discord_id}",
                color=color
            )
        
        embed.add_field(name="Status", value=f"{user_s.status.value}", inline=False)
        embed.add_field(
            name="Skills",
            value="```\n" + "\n".join([s.value for s in user_s.skills] if len(user_s.skills) > 0 else ["(None)\n"]) + "```",
            inline=False
        )
        embed.add_field(
            name="Rhythm Games",
            value="```\n" + "\n".join([r.value for r in user_s.rhythm_games] if len(user_s.rhythm_games) > 0 else ["(None)\n"]) + "```",
            inline=False
        )
        
        # build view
        await self.build_view(user_s)

        return embed
    
    
    async def build_view(self, user_s:schema.User):
        # status
        self.change_status.disabled = False
        if user_s.status == model.Status.online:
            self.change_status.label = "Change status to offline"
            self.change_status.custom_id = "update_user:status:offline"
        else:
            self.change_status.label = "Change status to online"
            self.change_status.custom_id = "update_user:status:online"
            
        # skills
        self.change_skills.disabled = False
        self.change_skills.options = [
            discord.SelectOption(
                label=s.value,
                value=s.value,
                default=(s in user_s.skills)
            ) for s in model.Skills
        ]
        
        # rhythm games
        self.change_rhythm_games.disabled = False
        self.change_rhythm_games.options = [
            discord.SelectOption(
                label=r.value,
                value=r.value,
                default=(r in user_s.rhythm_games)
            ) for r in model.RhythmGames
        ]
    
    
    @discord.ui.button(style=discord.ButtonStyle.grey, label="dummy", disabled=True, row=1)
    async def change_status(self, button:discord.ui.Button, interaction:discord.Interaction):
        # check permission
        if (member := (await security.discord_check_user_and_auto_register(interaction, False))) is None:
            return
        
        if member.id != self.discord_id:
            await interaction.response.send_message(f"You are not the owner of this view", ephemeral=True)
            return
        
        # update user
        target_status = model.Status.online if button.custom_id == "update_user:status:online" else model.Status.offline
        try:
            async with database.with_get_db() as session:
                async with session.begin():
                    db_user = await crud.update_user(session, discord_id=member.id, status=target_status)
        except Exception as e:
            logger.error(f"fail to update User (discord_id={member.id}): {str(e)}")
            await interaction.response.send_message(f"fail to update User (discord_id={member.id})", ephemeral=True)
            return
        
        # return
        embed = await self.build_embed_and_view()
        await interaction.response.edit_message(embed=embed, view=self)
        return
    
    
    @discord.ui.select(
        placeholder="Change skills...",
        disabled=True,
        row=2,
        min_values=0, max_values=len(model.Skills),
        options=[discord.SelectOption(label=f"dummy{_}") for _ in range(len(model.Skills))]
    )    
    async def change_skills(self, select:discord.ui.Select, interaction:discord.Interaction):
        # check permission
        if (member := (await security.discord_check_user_and_auto_register(interaction, False))) is None:
            return
        
        if member.id != self.discord_id:
            await interaction.response.send_message(f"You are not the owner of this view", ephemeral=True)
            return
        
        # update user
        skills = [model.Skills(s) for s in select.values]
        try:
            async with database.with_get_db() as session:
                async with session.begin():
                    db_user = await crud.update_user(session, discord_id=member.id, skills=skills)
        except Exception as e:
            logger.error(f"fail to update User (discord_id={member.id}): {str(e)}")
            await interaction.response.send_message(f"fail to update User (discord_id={member.id})", ephemeral=True)
            return
        
        # return
        embed = await self.build_embed_and_view()
        await interaction.response.edit_message(embed=embed, view=self)
        return
    
    
    @discord.ui.select(
        placeholder="Change rhythm games...",
        disabled=True,
        row=3,
        min_values=0, max_values=len(model.RhythmGames),
        options=[discord.SelectOption(label=f"dummy{_}") for _ in range(len(model.RhythmGames))]
    )
    async def change_rhythm_games(self, select:discord.ui.Select, interaction:discord.Interaction):
        # check permission
        if (member := (await security.discord_check_user_and_auto_register(interaction, False))) is None:
            return
        
        if member.id != self.discord_id:
            await interaction.response.send_message(f"You are not the owner of this view", ephemeral=True)
            return
        
        # update user
        rhythm_games = [model.RhythmGames(r) for r in select.values]
        try:
            async with database.with_get_db() as session:
                async with session.begin():
                    db_user = await crud.update_user(session, discord_id=member.id, rhythm_games=rhythm_games)
        except Exception as e:
            logger.error(f"fail to update User (discord_id={member.id}): {str(e)}")
            await interaction.response.send_message(f"fail to update User (discord_id={member.id})", ephemeral=True)
            return
        
        # return
        embed = await self.build_embed_and_view()
        await interaction.response.edit_message(embed=embed, view=self)
        return

        
# cog
class User(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    @discord.slash_command(name="user", description="User Panel")
    async def user_menu(self, ctx:discord.ApplicationContext):
        # check permission
        if (member := (await security.discord_check_user_and_auto_register(ctx, False))) is None:
            return
        
        view = UserMenu(self.bot, member.id)
        embed = await view.build_embed_and_view()
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)


def setup(bot:commands.Bot):
    bot.add_cog(User(bot))