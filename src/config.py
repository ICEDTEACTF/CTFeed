import asyncio

from pydantic_settings import BaseSettings, SettingsConfigDict

# settings
class Settings(BaseSettings):
    # Discord bot configuration
    DISCORD_BOT_TOKEN:str
    GUILD_ID:int
    # from database
    ANNOUNCEMENT_CHANNEL_ID:int=-1
    CTF_CHANNEL_CATEGORY_ID:int=-1
    ARCHIVE_CATEGORY_ID:int=-1
    PM_ROLE_ID:int=-1
    MEMBER_ROLE_ID:int=-1
    
    # HTTP API configuration
    HTTP_SECRET_KEY:str
    HTTP_FRONTEND_URL:str               # for example https://example.com
    HTTP_COOKIE_DOMAIN:str              # for example .example.com
    HTTP_COOKIE_MAX_AGE:int=60*60*24*30 # in seconds, default 30 days
    
    # Discord OAuth2 configuration
    DISCORD_OAUTH2_CLIENT_ID:str
    DISCORD_OAUTH2_CLIENT_SECRET:str
    DISCORD_OAUTH2_REDIRECT_URI:str=""
    
    # CTFTime configuration
    CHECK_INTERVAL_MINUTES:int
    CTFTIME_API:str="https://ctftime.org/api/v1"
    CTFTIME_API_EVENT:str=""
    CTFTIME_API_TEAM:str=""
    DATABASE_SEARCH_DAYS:int=-90        # search events which finish after now_days+DATABASE_SEARCH_DAYS (for example: now_days+(-90)) in database
    
    # Database configuration
    DATABASE_URL:str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

settings.DISCORD_OAUTH2_REDIRECT_URI = settings.HTTP_FRONTEND_URL + "/auth/login"
settings.CTFTIME_API_EVENT = settings.CTFTIME_API + "/events/"
settings.CTFTIME_API_TEAM = settings.CTFTIME_API + "/teams/"

# lock
# for the following members
# - ANNOUNCEMENT_CHANNEL_ID
# - CTF_CHANNEL_CATEGORY_ID
# - ARCHIVE_CATEGORY_ID
# - PM_ROLE_ID
# - MEMBER_ROLE_ID
settings_lock = asyncio.Lock()
