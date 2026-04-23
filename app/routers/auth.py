from fastapi import APIRouter

from app.dependencies.services import UserServiceDep
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    service: UserServiceDep,
) -> LoginResponse:
    """выполняет учебный логин и выдает токен"""

    return service.login(payload.username)
