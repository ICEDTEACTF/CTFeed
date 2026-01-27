from typing import Any
import enum

from sqlalchemy import (
    Integer, BigInteger, String, Boolean,
    Enum, ARRAY,
    ForeignKey,
    CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pydantic import BaseModel
import discord

Base = declarative_base()

# Config
class ConfigType(enum.Enum):
    CHANNEL="channel"
    CATEGORY="category"
    ROLE="role"


class ConfigInfo(BaseModel):
    name:str
    data_type:Any
    config_type:ConfigType
    select_type:Any     # discord.ComponentType
    description:str


config_info = {
    "ANNOUNCEMENT_CHANNEL_ID": ConfigInfo(
        name="ANNOUNCEMENT_CHANNEL_ID",
        data_type=int,
        config_type=ConfigType.CHANNEL,
        select_type=discord.ComponentType.channel_select,
        description="The channel which announcements send to"
    ),
    "CTF_CHANNEL_CATEGORY_ID": ConfigInfo(
        name="CTF_CHANNEL_CATEGORY_ID",
        data_type=int,
        config_type=ConfigType.CATEGORY,
        select_type=discord.ComponentType.channel_select,
        description="The category which CTF channels belong to"
    ),
    "ARCHIVE_CATEGORY_ID": ConfigInfo(
        name="ARCHIVE_CATEGORY_ID",
        data_type=int,
        config_type=ConfigType.CATEGORY,
        select_type=discord.ComponentType.channel_select,
        description="The category which archived CTF channels belong to"
    ),
    "PM_ROLE_ID": ConfigInfo(
        name="PM_ROLE_ID",
        data_type=int,
        config_type=ConfigType.ROLE,
        select_type=discord.ComponentType.role_select,
        description="The role for project managers"
    ),
    "MEMBER_ROLE_ID": ConfigInfo(
        name="MEMBER_ROLE_ID",
        data_type=int,
        config_type=ConfigType.ROLE,
        select_type=discord.ComponentType.role_select,
        description="The role for members"
    )
}

class Config(Base):
    __tablename__ = "Config"
    
    id:Mapped[int] = mapped_column(Integer, primary_key=True, index=True, unique=True, nullable=False, autoincrement=False, default=1)
    announcement_channel_id:Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, default=-1)
    ctf_channel_category_id:Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, default=-1)
    archive_category_id:Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, default=-1)
    pm_role_id:Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, default=-1)
    member_role_id:Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, default=-1)
    
    __table_args__ = (
        CheckConstraint("id = 1", name="config_only_one_row"),
    )
