from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.user import User
from app.models.role import Role, sys_user_role
from app.models.menu import Menu, sys_role_menu
from app.schemas.auth import (
    LoginRequest, LoginResponse, UserInfo, 
    UserCreate, UserUpdate, UserResponse,
    RoleCreate, RoleUpdate, RoleResponse,
    MenuCreate, MenuResponse
)
from app.utils.deps import get_current_user

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """User login"""
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # Get user roles
    roles = db.execute(
        text("""
            SELECT r.role_key FROM sys_role r
            JOIN sys_user_role ur ON r.id = ur.role_id
            WHERE ur.user_id = :user_id AND r.status = 1
        """),
        {"user_id": user.id}
    ).fetchall()
    role_keys = [r[0] for r in roles]
    
    # Get user permissions
    permissions = db.execute(
        text("""
            SELECT DISTINCT m.permission FROM sys_menu m
            JOIN sys_role_menu rm ON m.id = rm.menu_id
            JOIN sys_user_role ur ON rm.role_id = ur.role_id
            WHERE ur.user_id = :user_id AND m.status = 1 AND m.permission IS NOT NULL
        """),
        {"user_id": user.id}
    ).fetchall()
    permission_list = [p[0] for p in permissions if p[0]]
    
    # Create token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        user_info=UserInfo(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            phone=user.phone,
            roles=role_keys,
            permissions=permission_list
        )
    )


@router.get("/info", response_model=UserInfo)
async def get_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user info"""
    # Get user roles
    roles = db.execute(
        text("""
            SELECT r.role_key FROM sys_role r
            JOIN sys_user_role ur ON r.id = ur.role_id
            WHERE ur.user_id = :user_id AND r.status = 1
        """),
        {"user_id": current_user.id}
    ).fetchall()
    role_keys = [r[0] for r in roles]
    
    # Get user permissions
    permissions = db.execute(
        text("""
            SELECT DISTINCT m.permission FROM sys_menu m
            JOIN sys_role_menu rm ON m.id = rm.menu_id
            JOIN sys_user_role ur ON rm.role_id = ur.role_id
            WHERE ur.user_id = :user_id AND m.status = 1 AND m.permission IS NOT NULL
        """),
        {"user_id": current_user.id}
    ).fetchall()
    permission_list = [p[0] for p in permissions if p[0]]
    
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        nickname=current_user.nickname,
        email=current_user.email,
        phone=current_user.phone,
        roles=role_keys,
        permissions=permission_list
    )


@router.get("/menus", response_model=List[MenuResponse])
async def get_user_menus(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user accessible menus"""
    # Check if admin role
    is_admin = db.execute(
        text("""
            SELECT 1 FROM sys_user_role ur
            JOIN sys_role r ON ur.role_id = r.id
            WHERE ur.user_id = :user_id AND r.role_key = 'admin'
        """),
        {"user_id": current_user.id}
    ).first()
    
    if is_admin:
        # Admin gets all menus
        menus = db.query(Menu).filter(Menu.status == 1).order_by(Menu.sort).all()
    else:
        # Get menus based on role
        menu_ids = db.execute(
            text("""
                SELECT DISTINCT rm.menu_id FROM sys_role_menu rm
                JOIN sys_user_role ur ON rm.role_id = ur.role_id
                WHERE ur.user_id = :user_id
            """),
            {"user_id": current_user.id}
        ).fetchall()
        menu_ids = [m[0] for m in menu_ids]
        menus = db.query(Menu).filter(
            Menu.id.in_(menu_ids),
            Menu.status == 1
        ).order_by(Menu.sort).all()
    
    # Build menu tree
    def build_tree(parent_id: int = 0):
        result = []
        for menu in menus:
            if menu.parent_id == parent_id:
                children = build_tree(menu.id)
                menu_dict = MenuResponse(
                    id=menu.id,
                    parent_id=menu.parent_id,
                    title=menu.title,
                    path=menu.path,
                    component=menu.component,
                    icon=menu.icon,
                    sort=menu.sort,
                    menu_type=menu.menu_type or 2,
                    permission=menu.permission,
                    status=menu.status,
                    children=children
                )
                result.append(menu_dict)
        return result
    
    return build_tree(0)
