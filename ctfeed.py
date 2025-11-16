#!/usr/bin/env python3

import discord
from discord import embeds
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

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(intents=intents)

known_events = load_known_events()

emoji = "🚩"

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
    category_name = "Incoming/Running CTF"
    guild = ctx.guild
    category = discord.utils.get(ctx.guild.categories, name=category_name)

    if category is None:
        await ctx.send(f"Category '{category_name}' not found.")
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(view_channel=True),
        guild.me: discord.PermissionOverwrite(view_channel=True)
    }

    try:
        new_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        msg = await new_channel.send(
            embed = discord.Embed(
                title=f"{ctx.author.display_name} 發起了 {channel_name}！",
            )
        )

        public_msg = await ctx.send(
            embed = discord.Embed(
                title=f"新CTF頻道創建{channel_name}",
                description=f"加入請按下面的Emoji{emoji}"
            )
        )

        await public_msg.add_reaction(emoji)
        bot.ctf_join_message_id = public_msg.id
        bot.ctf_channel = new_channel
    except Exception as e:
        await ctx.send(f"Failed to create channel: {e}")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id != getattr(bot, "ctf_join_message_id", None):
        return

    if str(payload.emoji) != emoji:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member.bot:
        return

    channel = bot.ctf_channel
    await channel.set_permissions(member, view_channel=True)
    print(f"{member} 已加入 {channel.name}")

if __name__ == "__main__":
    main()
