"""
HORNET Dashboard Authentication
JWT-based authentication for dashboard access.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import hashlib

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import structlog

try:
    from jose import JWTError, jwt
except ImportError:
    jwt = None
    JWTError = Exception

from hornet.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    sub: str  # user_id
    tenant_id: str
    role: str
    exp: datetime


class User(BaseModel):
    id: str
    email: str
    tenant_id: str
    role: str  # admin, analyst, viewer
    name: Optional[str] = None


class AuthManager:
    """Manages authentication and authorization."""
    
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        # Demo users (would be in database)
        self._demo_users = {
            "admin@hornet.local": {
                "id": "user_admin",
                "password_hash": self._hash_password("admin123"),
                "tenant_id": "demo",
                "role": "admin",
                "name": "Admin User",
            },
            "analyst@hornet.local": {
                "id": "user_analyst",
                "password_hash": self._hash_password("analyst123"),
                "tenant_id": "demo",
                "role": "analyst",
                "name": "Security Analyst",
            },
        }
    
    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self._hash_password(plain_password) == hashed_password
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: timedelta = None) -> str:
        if jwt is None:
            raise HTTPException(status_code=500, detail="JWT library not installed")
        
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.ALGORITHM)
    
    def create_refresh_token(self, user_id: str) -> str:
        return self.create_access_token(
            {"sub": user_id, "type": "refresh"},
            expires_delta=timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        )
    
    def verify_token(self, token: str) -> Optional[TokenPayload]:
        if jwt is None:
            return None
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.ALGORITHM])
            return TokenPayload(
                sub=payload["sub"],
                tenant_id=payload.get("tenant_id", ""),
                role=payload.get("role", "viewer"),
                exp=datetime.fromtimestamp(payload["exp"]),
            )
        except JWTError:
            return None
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user_data = self._demo_users.get(email)
        if not user_data:
            return None
        if not self.verify_password(password, user_data["password_hash"]):
            return None
        return User(
            id=user_data["id"],
            email=email,
            tenant_id=user_data["tenant_id"],
            role=user_data["role"],
            name=user_data["name"],
        )
    
    def generate_api_key(self, tenant_id: str) -> str:
        random_part = secrets.token_urlsafe(24)
        return f"hnt_{tenant_id}_{random_part}"


auth_manager = AuthManager()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[User]:
    """Get current user from JWT token."""
    if not credentials:
        return None
    
    token_data = auth_manager.verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In production, would load user from database
    return User(
        id=token_data.sub,
        email="",
        tenant_id=token_data.tenant_id,
        role=token_data.role,
    )


async def require_auth(user: User = Depends(get_current_user)) -> User:
    """Require authentication."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*roles: str):
    """Require specific role(s)."""
    async def role_checker(user: User = Depends(require_auth)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role} not authorized. Required: {roles}",
            )
        return user
    return role_checker


# Convenience dependencies
require_admin = require_role("admin")
require_analyst = require_role("admin", "analyst")
require_viewer = require_role("admin", "analyst", "viewer")
