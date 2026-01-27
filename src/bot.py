import logging
import asyncio
import glob
import pathlib

from discord.ext import commands
import discord

from src.config import settings

# logging
logging.getLogger("discord.client").setLevel(logging.ERROR)
logger = logging.getLogger("uvicorn")

# task
task:asyncio.Task = None

# bot
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Bot logged in: {bot.user}")

# cogs
def load_cogs():
    for filename in glob.glob("./src/cog/*.py"):
        name = pathlib.Path(filename).name.split(".")[0]
        extension_name = f"src.cog.{name}"
        try:
            bot.load_extension(extension_name)
            logger.info(f"{extension_name} loaded")
        except Exception as e:
            logger.error(f"fail to load {extension_name}: {str(e)}")


# startup and shutdown
async def main():
    load_cogs()
    
    async with bot:
        await bot.start(settings.DISCORD_BOT_TOKEN)


async def start_bot():
    global task
    
    logger.info("Starting CTF bot...")
    task = asyncio.create_task(main())


async def stop_bot():
    if task is not None:
        task.cancel()
        

# get bot
async def get_bot() -> commands.Bot:
    return bot
