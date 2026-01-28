import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.ext.asyncio import AsyncSession
import discord

from src.database.database import fastapi_get_db
from src.config import settings
from src.backend import security
from src import crud
from src import schema

# logger
logger = logging.getLogger("uvicorn")

# oauth
DISCORD_API = "https://discord.com/api"
DISCORD_API_TOKEN = DISCORD_API + "/oauth2/token"
DISCORD_API_AUTHORIZE = DISCORD_API + "/oauth2/authorize"
DISCORD_API_ME = DISCORD_API + "/users/@me"

oauth = OAuth()
oauth.register(
    name="discord",
    client_id=settings.DISCORD_OAUTH2_CLIENT_ID,
    client_secret=settings.DISCORD_OAUTH2_CLIENT_SECRET,
    access_token_url=DISCORD_API_TOKEN,
    access_token_params=None,
    authorize_url=DISCORD_API_AUTHORIZE,
    authorize_params=None,
    api_base_url=DISCORD_API_ME,
    client_kwargs={'scope': 'identify email guilds connections'},
)

# router
router = APIRouter(prefix="/auth")

# auth
@router.get("/discord")
async def redirect_discord(request:Request):
    return (await oauth.discord.authorize_redirect(
        request,
        settings.DISCORD_OAUTH2_REDIRECT_URI
    ))


@router.get("/login")
async def login(request:Request):
    # get token
    try:
        token = await oauth.discord.authorize_access_token(request)
    except Exception:
        raise HTTPException(400)
    
    # get user info
    try:
        user_resp = await oauth.discord.get(DISCORD_API_ME, token=token)
        user_info = user_resp.json()
        discord_id:int = int(user_info["id"])
    except Exception:
        raise HTTPException(500)
    
    # check permission and login (or register)
    member = await security.check_user_and_auto_register(discord_id, force_pm=False, auto_register=True)
    
    # login
    request.session["discord_id"] = discord_id
    return RedirectResponse(settings.HTTP_FRONTEND_URL)


@router.get("/logout")
async def logout(request:Request):
    request.session["discord_id"] = 0
    return RedirectResponse(settings.HTTP_FRONTEND_URL)

# me
@router.get("/me") # todo
async def me(
    session:AsyncSession=Depends(fastapi_get_db),
    member:discord.Member=Depends(security.fastapi_check_user)
) -> schema.General:
    return schema.General(success=True, message=str(member.id))