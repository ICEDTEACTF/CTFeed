from .general import General
from .config import Config, ConfigResponse
from .user import UserSimple, User, DiscordUser, UpdateUser
from .event import EventSimple, Event

User.model_rebuild()
Event.model_rebuild()