import logging

from fastapi import APIRouter

# logger
logger = logging.getLogger("uvicorn")

# router
router = APIRouter(prefix="/auth")