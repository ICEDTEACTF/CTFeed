from discord.ext import commands
import discord

from src.config import settings

# constants
GITHUB_URL = "https://github.com/ICEDTEACTF/CTFeed"

# view
class HelpMenu(discord.ui.View):
    def __init__(self, bot:commands.Bot):
        super().__init__(timeout=None)

        self.bot = bot
        self._build_view()


    def _build_view(self):
        # link buttons
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="GitHub",
            url=GITHUB_URL
        ))
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Dashboard",
            url=settings.HTTP_FRONTEND_URL
        ))

        return


    async def build_embed_and_view(self) -> discord.Embed:
        # build embed
        bot_name = self.bot.user.name if self.bot.user is not None else "ICEDTEA CTF bot"
        description = (
            "CTFeed is a Discord bot that tracks CTFTime events, "
            "manages event channels, and provides a simple dashboard."
        )
        commands_info = [
            "`/help` - Show this help message",
            "`/ctfmenu` - Browse and manage CTFTime events",
            "`/user` - View and update your user profile",
            "`/config` - Configure guild settings (admin only)"
        ]

        embed = discord.Embed(
            title=f"{bot_name} Help",
            description=description,
            color=discord.Color.green()
        )
        embed.add_field(
            name="Commands",
            value="\n".join(commands_info),
            inline=False
        )
        embed.set_footer(text=f"Commit: {settings.COMMIT_ID}")

        return embed


# cog
class Help(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot


    @discord.slash_command(name="help", description="Help Panel")
    async def help_menu(self, ctx:discord.ApplicationContext):
        view = HelpMenu(self.bot)
        embed = await view.build_embed_and_view()
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)


def setup(bot:commands.Bot):
    bot.add_cog(Help(bot))
