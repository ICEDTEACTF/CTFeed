from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
import logging

import aiohttp

from src.config import settings

logger = logging.getLogger(__name__)

async def fetch_ctf_events(event_id:Optional[int]=None) -> List[Dict[str, Any]]:
    params = {
        "limit": 20, # todo 考慮加入一個參數，讓系統會一直索取直到 start 到達這個參數
        "start": int(datetime.now(timezone.utc).timestamp())
    }
    
    url = settings.CTFTIME_API_EVENT
    if event_id is not None:
        # for example: "https://ctftime.org/api/v1/events/2345/"
        url = f"{url}{event_id}/"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                if event_id is not None:
                    return [await response.json()]
                return (await response.json())
            elif response.status == 404:
                return []
            else:
                raise RuntimeError(f"API returned {response.status} (with event_id={event_id})")


async def fetch_team_info(team_id) -> Tuple[Optional[str], Optional[str]]:
    url = f"{settings.CTFTIME_API_TEAM}{team_id}/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    team_data = await response.json()
                    return team_data.get("country"), team_data.get("name")
    except Exception as e:
        logger.error(f"Error fetching team info: {e}")
    return None, None
