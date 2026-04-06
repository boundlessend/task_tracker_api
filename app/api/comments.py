from app.dependencies.services import get_comment_service
from app.routers.comments import router

__all__ = ["get_comment_service", "router"]
