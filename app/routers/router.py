from fastapi import APIRouter

from app.routers.auth import router as auth_router
from app.routers.comments import router as comments_router
from app.routers.health import router as health_router
from app.routers.tasks import router as tasks_router
from app.routers.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(tasks_router)
api_router.include_router(users_router)
api_router.include_router(comments_router)
