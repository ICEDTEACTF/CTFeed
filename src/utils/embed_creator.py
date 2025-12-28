import discord
import pytz
import logging
from datetime import datetime
from src.utils.ctf_api import fetch_team_info
from src.utils.country_flags import get_country_info

logger = logging.getLogger(__name__)


async def create_event_embed(event, title:str):
    start_time_utc = datetime.fromisoformat(event["start"].replace("Z", "+00:00"))
    finish_time_utc = datetime.fromisoformat(event["finish"].replace("Z", "+00:00"))

    taipei_tz = pytz.timezone("Asia/Taipei")
    start_time_taipei = start_time_utc.astimezone(taipei_tz)
    finish_time_taipei = finish_time_utc.astimezone(taipei_tz)

    color = discord.Color.green()

    organizer_info = []
    first_country_flag = ""
    if event.get("organizers"):
        logger.info(f"Processing {len(event['organizers'])} organizers")
        for i, org in enumerate(event["organizers"][:3]):
            try:
                country_code, team_name = await fetch_team_info(org["id"])
                logger.info(
                    f"Organizer {org['name']} (ID: {org['id']}) country: {country_code}"
                )
                country_flag, country_name = get_country_info(country_code)
                if i == 0:
                    first_country_flag = country_flag
                organizer_info.append(f"{country_flag} {org['name']}")
            except Exception as e:
                logger.error(f"Failed to fetch organizer {org['name']} info: {e}")
                organizer_info.append(f"🌍 {org['name']}")

    title_with_flag = event["title"]
    if first_country_flag:
        title_with_flag = f"{first_country_flag} {event['title']}"

    embed = discord.Embed(
        title=title, description=f"**{title_with_flag}**", color=color
    )

    embed.add_field(
        name="🕐 比賽時間",
        value=f"**開始：** {start_time_taipei.strftime('%m月%d日 %H:%M')} (台北) | {start_time_utc.strftime('%H:%M UTC')}\n"
        f"**結束：** {finish_time_taipei.strftime('%m月%d日 %H:%M')} (台北) | {finish_time_utc.strftime('%H:%M UTC')}\n"
        f"**持續：** {event['duration']['days']}天 {event['duration']['hours']}小時",
        inline=False,
    )

    details = []
    details.append(f"**評分：** {event.get('weight', 0)}")
    if event.get("restrictions"):
        details.append(f"**限制：** {event['restrictions']}")

    if organizer_info:
        if len(organizer_info) == 1:
            details.append(f"**主辦：** {organizer_info[0]}")
        else:
            details.append(f"**主辦：** {', '.join(organizer_info)}")

    embed.add_field(name="比賽詳情", value="\n".join(details), inline=True)

    links = []
    if event.get("url"):
        links.append(f"🌐 **官方網站：** {event['url']}")

    ctftime_url = f"https://ctftime.org/event/{event['id']}"
    links.append(f"**CTFtime：** {ctftime_url}")

    if links:
        embed.add_field(name="🔗 相關連結", value="\n".join(links), inline=False)

    embed.set_footer(text=f"Event ID: {event['id']} | CTFtime.org")

    return embed