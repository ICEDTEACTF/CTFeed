from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Discord bot configuration
    DISCORD_BOT_TOKEN:str
    
    # CTFTime tracking configuration
    CTFTIME_API_URL:str="https://ctftime.org/api/v1/events/"
    TEAM_API_URL:str="https://ctftime.org/api/v1/teams/"
    CTFTIME_SEARCH_DAYS:int=+90
    DATABASE_SEARCH_DAYS:int=-90 # known events: finish > now_day+(-90)
    ANNOUNCEMENT_CHANNEL_NAME:str
    CHECK_INTERVAL_MINUTES:int
    
    # Database configuration
    DATABASE_URL:str="sqlite+aiosqlite:///data/database.db"
    
    # Notification (todo)
    #NOTIFY_BEFORE_EVENT:int = 1 * 24 * 60 * 60
    
    # Misc
    TIMEZONE:str
    EMOJI:str="🚩"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
