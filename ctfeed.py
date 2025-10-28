#!/usr/bin/env python3

import discord
from discord.ext import tasks, commands
import logging
import os

from src.config import DISCORD_BOT_TOKEN, ANNOUNCEMENT_CHANNEL_ID, CHECK_INTERVAL
from src.data_manager import load_known_events, save_known_events
from src.ctf_api import fetch_ctf_events
from src.embed_creator import create_event_embed

logging.basicConfig(level=logging.INFO)
logging.getLogger("discord.client").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

bot = commands.Bot(intents=discord.Intents.default())

known_events = load_known_events()


@bot.event
async def on_ready():
    logger.info(f"Bot logged in: {bot.user}")
    if known_events:
        logger.info(
            f"Loading data/known_events.json for {len(known_events)} known competitions"
        )
    else:
        logger.info(
            "No known competitions found, creating new file data/known_events.json"
        )
        save_known_events(set())
    check_new_events.start()


@tasks.loop(minutes=CHECK_INTERVAL)
async def check_new_events():
    global known_events

    events = await fetch_ctf_events()

    channel_name = ANNOUNCEMENT_CHANNEL_ID
    if not channel_name:
        logger.error("Please set ANNOUNCEMENT_CHANNEL_ID in .env file")
        logger.error("For example: ANNOUNCEMENT_CHANNEL_ID=ctftime")
        logger.error("Please check if the .env file is correctly set")
        await bot.close()
        return

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

    new_events_found = False
    for event in events:
        event_id = event["id"]
        if event_id not in known_events:
            known_events.add(event_id)
            new_events_found = True

            embed = await create_event_embed(event)
            try:
                await channel.send(embed=embed)
                logger.info(f"Sent new event notification: {event['title']}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

    if new_events_found:
        save_known_events(known_events)


@check_new_events.before_loop
async def before_check():
    await bot.wait_until_ready()


def main():
    if not DISCORD_BOT_TOKEN:
        print("Please set DISCORD_BOT_TOKEN in .env file")
        exit(1)

    print("Start CTF Bot...")
    bot.run(DISCORD_BOT_TOKEN)


@bot.slash_command(name = "create_ctf_channel", description = "Create a CTF channel in the CTF category")
async def create_CTF_channel(ctx, channel_name:str):
    category_name = "CTF"
    guild = ctx.guild
    category = discord.utils.get(ctx.guild.categories, name=category_name)

    if category is None:
        await ctx.send(f"Category '{category_name}' not found.")
        return

    try:
        new_channel = await guild.create_text_channel(channel_name, category=category)
        await ctx.send(f"Channel '{new_channel.name}' created in category '{category_name}'.")
    except Exception as e:
        await ctx.send(f"Failed to create channel: {e}")


if __name__ == "__main__":
    main()
