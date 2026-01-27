from typing import List, Any

from pydantic import BaseModel

class Config(BaseModel):
    key:str
    description:str
    message:str
    value:Any
    ok:bool


class ConfigResponse(BaseModel):
    guild_id:int
    guild_name:str
    config:List[Config]