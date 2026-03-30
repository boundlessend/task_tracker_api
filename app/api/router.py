from fastapi import APIRouter

from app.api.comments import router as comments_router
from app.api.health import router as health_router
from app.api.tasks import router as tasks_router
from app.api.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(tasks_router)
api_router.include_router(users_router)
api_router.include_router(comments_router)
