#!/usr/bin/env python3

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings, settings_lock
from src.database import database
from src import crud
from src import schema
from src import bot

# logging
logger = logging.getLogger("uvicorn")

# start and shutdown
@asynccontextmanager
async def lifespan(app:FastAPI):
    # startup
    ## initialize database
    try:
        await database.init_db()
    except Exception as e:
        logger.error(f"fail to initialize database: {str(e)}")
        raise
    
    ## initialize config
    try:
        async with database.with_get_db() as session:
            async with session.begin():
                config = await crud.create_or_update_config(session)
    except Exception as e:
        logger.error(f"fail to initialize Config in database: {str(e)}")
        raise
    
    async with settings_lock:
        settings.ANNOUNCEMENT_CHANNEL_ID = config.announcement_channel_id
        settings.CTF_CHANNEL_CATEGORY_ID = config.ctf_channel_category_id
        settings.ARCHIVE_CATEGORY_ID = config.archive_category_id
        settings.PM_ROLE_ID = config.pm_role_id
        settings.MEMBER_ROLE_ID = config.member_role_id
    
    ## start discord bot
    await bot.start_bot()
    
    # app run
    yield
    
    # shutdown
    ## stop discord bot
    await bot.stop_bot()


# app
app = FastAPI(debug=False, lifespan=lifespan)

# middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.HTTP_FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.HTTP_SECRET_KEY,
    domain=settings.HTTP_COOKIE_DOMAIN,
    path="/",
    same_site="Lax",
    https_only=True,
    max_age=settings.HTTP_COOKIE_MAX_AGE,
)

# router

# index
@app.get("/")
async def index() -> schema.General:
    return schema.General(
        success=True,
        message="Shirakami Fubuki is the cutest fox in the world!"
    )
