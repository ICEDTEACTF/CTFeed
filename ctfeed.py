#!/usr/bin/env python3

import logging
import asyncio
import glob
import pathlib

import discord
from discord.ext import commands

from src.config import settings
from src.database.database import init_db

# logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("discord.client").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

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


async def main():
    # setup
    
    # initializing database    
    logger.info("Initializing database...")
    await init_db()
    
    # start
    logger.info(f"Starting CTF Bot...")
    async with bot:
        await bot.start(settings.DISCORD_BOT_TOKEN)


# cogs
def load_cogs():
    for filename in glob.glob("./src/cogs/*.py"):
        name = pathlib.Path(filename).name.split(".")[0]
        extension_name = f"src.cogs.{name}"
        try:
            bot.load_extension(extension_name)
            logger.info(f"{extension_name} loaded")
        except Exception as e:
            logger.error(f"failed to load {extension_name}: {str(e)}")


if __name__ == "__main__":
    load_cogs()
    asyncio.run(main())
