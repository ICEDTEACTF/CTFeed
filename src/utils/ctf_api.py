from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import aiohttp
import logging

from src.config import settings

logger = logging.getLogger(__name__)


async def fetch_ctf_events(event_id:Optional[int]=None) -> List[Dict[str, Any]]:
    params = {
        "limit": 20,
        "start": int(datetime.now().timestamp()),
        "finish": int((datetime.now() + timedelta(days=settings.CTFTIME_SEARCH_DAYS)).timestamp()),
    }
    
    url = settings.CTFTIME_API_URL
    if not (event_id is None):
        # for example: "https://ctftime.org/api/v1/events/2345"
        url = f"{url}{event_id}/"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    if not (event_id is None):
                        return [await response.json()]
                    
                    return await response.json()
    except Exception as e:
        logger.error(f"API error: {e}")
    
    return []


async def fetch_team_info(team_id):
    url = f"{settings.TEAM_API_URL}{team_id}/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    team_data = await response.json()
                    return team_data.get("country"), team_data.get("name")
    except Exception as e:
        logger.error(f"Error fetching team info: {e}")
    return None, None
