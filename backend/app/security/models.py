from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    USER = "user"
    ANALYST = "analyst"
    ADMIN = "admin"


class Permission(str, Enum):
    CHAT = "chat"
    RAG_READ = "rag:read"
    RESEARCH = "research"
    DATA_READ = "data:read"
    DATA_WRITE = "data:write"
    ADMIN = "admin"


class TokenData(BaseModel):
    user_id: str
    role: Role
    permissions: list[Permission] = Field(default_factory=list)


class UserContext(BaseModel):
    user_id: str
    role: Role
    permissions: set[Permission] = Field(default_factory=set)
