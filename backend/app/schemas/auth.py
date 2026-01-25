from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_info: "UserInfo"


class UserInfo(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role_ids: List[int] = []


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[int] = None
    role_ids: Optional[List[int]] = None


class UserResponse(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: int
    create_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    role_name: str
    role_key: str


class RoleUpdate(BaseModel):
    role_name: Optional[str] = None
    role_key: Optional[str] = None
    status: Optional[int] = None


class RoleResponse(BaseModel):
    id: int
    role_name: str
    role_key: str
    status: int
    create_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class MenuCreate(BaseModel):
    parent_id: int = 0
    title: str
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort: int = 0
    menu_type: int = 2
    permission: Optional[str] = None


class MenuResponse(BaseModel):
    id: int
    parent_id: int
    title: str
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort: int
    menu_type: int
    permission: Optional[str] = None
    status: int
    children: List["MenuResponse"] = []

    class Config:
        from_attributes = True


LoginResponse.model_rebuild()
MenuResponse.model_rebuild()
