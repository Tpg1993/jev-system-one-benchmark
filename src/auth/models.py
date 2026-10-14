from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    BENCHMARK_ADMIN = "benchmark_admin"
    ANALYST = "analyst"
    USER = "user"
    SERVICE_ACCOUNT = "service_account"


class RoleLevel(int, Enum):
    USER = 1
    SERVICE_ACCOUNT = 1
    ANALYST = 2
    BENCHMARK_ADMIN = 3
    SUPER_ADMIN = 4


ROLE_HIERARCHY = {
    Role.SUPER_ADMIN: RoleLevel.SUPER_ADMIN,
    Role.BENCHMARK_ADMIN: RoleLevel.BENCHMARK_ADMIN,
    Role.ANALYST: RoleLevel.ANALYST,
    Role.USER: RoleLevel.USER,
    Role.SERVICE_ACCOUNT: RoleLevel.SERVICE_ACCOUNT,
}


class UserBase(BaseModel):
    email: EmailStr
    username: str
    role: Role = Role.USER
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class User(UserBase):
    id: str
    hashed_password: str

    @property
    def role_level(self) -> int:
        return ROLE_HIERARCHY.get(self.role, RoleLevel.USER).value


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    role_level: int


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[Role] = None
