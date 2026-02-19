from pydantic import BaseModel

# response schema
class DiscordTextChannel(BaseModel):
    id:int
    jump_url:str
    name:str


class DiscordCategoryChannel(BaseModel):
    id:int
    jump_url:str
    name:str


class DiscordRole(BaseModel):
    id:int
    name:str