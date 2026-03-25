"""
security/auth.py — JWT authentication + Role-Based Access Control
"""
from datetime import datetime, timedelta
from typing import Optional
import warnings

# Suppress bcrypt version warning from passlib
warnings.filterwarnings("ignore", ".*error reading bcrypt version.*")
warnings.filterwarnings("ignore", ".*trapped.*")

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import get_settings
from core.database import get_db, User

settings = get_settings()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Role hierarchy — which roles can access which content
ROLE_ACCESS_MAP = {
    "admin":   ["admin", "hr", "finance", "general"],
    "hr":      ["hr", "general"],
    "finance": ["finance", "general"],
    "general": ["general"],
}


def hash_password(password: str) -> str:
    """Hash password with bcrypt, truncating to 72 bytes max."""
    password_bytes = password.encode("utf-8")[:72]
    return pwd_context.hash(password_bytes.decode("utf-8", errors="ignore"))


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        plain_bytes = plain.encode("utf-8")[:72]
        return pwd_context.verify(
            plain_bytes.decode("utf-8", errors="ignore"), hashed
        )
    except Exception:
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Decode JWT and return the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user


def get_accessible_roles(user_role: str) -> list[str]:
    """Return all content roles this user can access based on their role."""
    return ROLE_ACCESS_MAP.get(user_role, ["general"])


def require_role(*roles: str):
    """
    Dependency factory to restrict endpoints to specific roles.
    Usage: Depends(require_role("admin", "hr"))
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required roles: {list(roles)}. "
                    f"Your role: {current_user.role}"
                )
            )
        return current_user
    return role_checker