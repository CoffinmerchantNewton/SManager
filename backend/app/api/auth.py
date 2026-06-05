from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..core.config import settings
from ..core.security import create_access_token, require_admin, verify_admin_credentials

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest):
    if not verify_admin_credentials(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return {
        "access_token": create_access_token(payload.username),
        "token_type": "bearer",
        "expires_in_minutes": settings.AUTH_TOKEN_EXPIRE_MINUTES,
        "username": payload.username,
    }


@router.get("/me")
def me(_: dict = Depends(require_admin)):
    return {"username": settings.ADMIN_USERNAME, "scope": "admin"}
