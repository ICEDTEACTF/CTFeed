from __future__ import annotations
from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from src.database import model

# post
class UpdateUser(BaseModel):
    status:Optional[model.Status] = None
    skills:Optional[List[model.Skills]] = None
    rhythm_games:Optional[List[model.RhythmGames]] = None


# get
class DiscordUser(BaseModel):
    display_name:str
    id:int
    name:str


class UserSimple(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    discord_id:int
    
    status:model.Status
    skills:List[model.Skills]
    rhythm_games:List[model.RhythmGames]
    
    discord:Optional[DiscordUser] = None


class User(UserSimple):
    events:List["EventSimple"]