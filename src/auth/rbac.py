from datetime import datetime, timedelta, timezone
from typing import Optional, Callable
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.config import settings
from src.auth.models import Role, RoleLevel, ROLE_HIERARCHY, User, TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8")[:72], salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# In-memory user store for demo/starter scaffold (can be replaced with SQLAlchemy / PostgreSQL)
FAKE_USERS_DB: dict[str, dict] = {
    settings.INIT_ADMIN_EMAIL: {
        "id": "usr_superadmin_01",
        "email": settings.INIT_ADMIN_EMAIL,
        "username": "superadmin",
        "hashed_password": get_password_hash(settings.INIT_ADMIN_PASSWORD),
        "role": Role.SUPER_ADMIN,
        "is_active": True,
    },
    "benchmark@example.com": {
        "id": "usr_bmadmin_02",
        "email": "benchmark@example.com",
        "username": "benchmarker",
        "hashed_password": get_password_hash("BenchPass123!"),
        "role": Role.BENCHMARK_ADMIN,
        "is_active": True,
    },
    "analyst@example.com": {
        "id": "usr_analyst_03",
        "email": "analyst@example.com",
        "username": "analyst",
        "hashed_password": get_password_hash("AnalystPass123!"),
        "role": Role.ANALYST,
        "is_active": True,
    },
    "user@example.com": {
        "id": "usr_user_04",
        "email": "user@example.com",
        "username": "standarduser",
        "hashed_password": get_password_hash("UserPass123!"),
        "role": Role.USER,
        "is_active": True,
    },
}


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        role_str: str = payload.get("role")
        if username is None or role_str is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=Role(role_str))
    except (JWTError, ValueError):
        raise credentials_exception

    user_dict = next((u for u in FAKE_USERS_DB.values() if u["username"] == token_data.username), None)
    if user_dict is None or not user_dict.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or non-existent user")

    return User(**user_dict)


def require_role_level(required_level: RoleLevel) -> Callable:
    """
    Dependency factory to enforce hierarchical role-based access control.
    Users with a role level >= required_level are authorized.
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_level = current_user.role_level
        if user_level < required_level.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Requires role level {required_level.name} ({required_level.value}), current level is {user_level}."
            )
        return current_user

    return role_checker
