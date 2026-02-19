from .general import General
from .config import Config, ConfigResponse, UpdateConfig
from .user import UserRole, UserSimple, User, DiscordUser, UpdateUser
from .event import EventSimple, Event, CreateCustomEvent, RelinkEvent
from .guild import DiscordTextChannel, DiscordCategoryChannel, DiscordRole

User.model_rebuild()

EventSimple.model_rebuild()
Event.model_rebuild()
