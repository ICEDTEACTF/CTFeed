from pydantic import BaseModel

class General(BaseModel):
    success:bool
    message:str