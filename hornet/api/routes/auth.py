"""HORNET Authentication Routes"""
from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
import structlog

from hornet.api.auth import auth_manager, User, require_auth

logger = structlog.get_logger()
router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return tokens."""
    user = await auth_manager.authenticate_user(request.email, request.password)
    
    if not user:
        logger.warning("login_failed", email=request.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    access_token = auth_manager.create_access_token({
        "sub": user.id,
        "tenant_id": user.tenant_id,
        "role": user.role,
    })
    refresh_token = auth_manager.create_refresh_token(user.id)
    
    logger.info("login_success", user_id=user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth_manager.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh access token."""
    token_data = auth_manager.verify_token(request.refresh_token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # In production, would verify token type and load user from database
    access_token = auth_manager.create_access_token({
        "sub": token_data.sub,
        "tenant_id": token_data.tenant_id,
        "role": token_data.role,
    })
    refresh_token = auth_manager.create_refresh_token(token_data.sub)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth_manager.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me")
async def get_current_user(user: User = Depends(require_auth)):
    """Get current user info."""
    return {
        "id": user.id,
        "tenant_id": user.tenant_id,
        "role": user.role,
        "name": user.name,
    }


@router.post("/logout")
async def logout(user: User = Depends(require_auth)):
    """Logout (invalidate tokens)."""
    # In production, would add token to blacklist
    logger.info("logout", user_id=user.id)
    return {"message": "Logged out successfully"}
