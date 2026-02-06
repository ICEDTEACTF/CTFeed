#!/usr/bin/env python3

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.database import database
from src.backend.config import update_config_cache
from src.utils import ctf_api
from src import crud
from src import schema
from src import bot
from src import router

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
        logger.critical(f"fail to initialize database: {str(e)}")
        raise
    
    ## initialize config
    try:
        async with database.with_get_db() as session:
            async with session.begin():
                config = await crud.create_or_update_config(session)
    except Exception as e:
        logger.critical(f"fail to initialize Config in database: {str(e)}")
        raise
    await update_config_cache(config)
    
    ## initialize aiohttp.ClientSession in src.utils.ctf_api
    try:
        await ctf_api.init_session()
    except Exception as e:
        logger.critical(f"fail to initialize aiohttp.ClientSession in src.utils.ctf_api")
        raise
    
    ## start discord bot
    await bot.start_bot()
    
    # app run
    yield
    
    # shutdown
    ## stop discord bot
    await bot.stop_bot()
    
    ## close aiohttp.ClientSession in src.utils.ctf_api
    try:
        await ctf_api.close_session()
    except Exception as e:
        logger.critical(f"fail to stop aiohttp.ClientSession in src.utils.ctf_api")


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
app.include_router(router.auth_router)
app.include_router(router.user_router)
app.include_router(router.ctf_router)

# index
@app.get("/", tags=["Shirakami Fubuki"])
async def index() -> schema.General:
    return schema.General(
        success=True,
        message="Shirakami Fubuki is the cutest fox in the world!"
    )
