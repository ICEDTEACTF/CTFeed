from sqlalchemy import Column, String, Integer, ForeignKey, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Event(Base):
    __tablename__ = 'events'
    
    # id
    event_id = Column(Integer, primary_key=True, index=True, nullable=False, unique=True, autoincrement=False)

    # event info
    title = Column(String, nullable=False)
    start = Column(Integer, nullable=False)
    finish = Column(Integer, nullable=False)
    
    # discord
    channel_id = Column(Integer, nullable=True, unique=True, default=None)
    

class CustomChannel(Base):
    __tablename__ = 'custom_channel'
    
    # discord
    channel_id = Column(Integer, primary_key=True, index=True, nullable=False, unique=True, autoincrement=False)