from __future__ import annotations

from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict


# request schema
class CreateCustomEvent(BaseModel):
    title:str


class RelinkEvent(BaseModel):
    channel_id:int


# response schema
class EventSimple(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id:int
    archived:bool
    
    event_id:Optional[int]=None
    title:str
    start:Optional[int]=None
    finish:Optional[int]=None
    
    channel_id:Optional[int]=None
    channel:Optional["DiscordTextChannel"]=None
    scheduled_event_id:Optional[int]=None
    
    # extra attrbutes
    now_running:Optional[bool]=None
    type:Literal["ctftime", "custom"]


class Event(EventSimple):
    users:List["UserSimple"]
