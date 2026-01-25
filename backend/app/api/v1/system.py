from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.role import Role, sys_user_role
from app.models.menu import Menu, sys_role_menu
from app.schemas.auth import (
    UserCreate, UserUpdate, UserResponse,
    RoleCreate, RoleUpdate, RoleResponse,
    MenuCreate, MenuResponse
)
from app.utils.deps import get_current_user

router = APIRouter()


# ============ User Management ============

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all users"""
    users = db.query(User).all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserResponse)
async def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new user"""
    # Check if username exists
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        nickname=data.nickname,
        email=data.email,
        phone=data.phone
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Assign roles
    for role_id in data.role_ids:
        db.execute(
            text("INSERT INTO sys_user_role (user_id, role_id) VALUES (:user_id, :role_id)"),
            {"user_id": user.id, "role_id": role_id}
        )
    db.commit()
    
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    update_data = data.model_dump(exclude_unset=True, exclude={"role_ids"})
    for key, value in update_data.items():
        setattr(user, key, value)
    
    # Update roles if provided
    if data.role_ids is not None:
        db.execute(
            text("DELETE FROM sys_user_role WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        for role_id in data.role_ids:
            db.execute(
                text("INSERT INTO sys_user_role (user_id, role_id) VALUES (:user_id, :role_id)"),
                {"user_id": user_id, "role_id": role_id}
            )
    
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete user"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # Delete role associations
    db.execute(
        text("DELETE FROM sys_user_role WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    
    db.delete(user)
    db.commit()
    return {"message": "删除成功"}


# ============ Role Management ============

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all roles"""
    roles = db.query(Role).all()
    return [RoleResponse.model_validate(r) for r in roles]


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new role"""
    if db.query(Role).filter(Role.role_key == data.role_key).first():
        raise HTTPException(status_code=400, detail="角色标识已存在")
    
    role = Role(role_name=data.role_name, role_key=data.role_key)
    db.add(role)
    db.commit()
    db.refresh(role)
    return RoleResponse.model_validate(role)


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update role"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(role, key, value)
    
    db.commit()
    db.refresh(role)
    return RoleResponse.model_validate(role)


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete role"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    if role.role_key == "admin":
        raise HTTPException(status_code=400, detail="不能删除管理员角色")
    
    # Delete associations
    db.execute(
        text("DELETE FROM sys_role_menu WHERE role_id = :role_id"),
        {"role_id": role_id}
    )
    db.execute(
        text("DELETE FROM sys_user_role WHERE role_id = :role_id"),
        {"role_id": role_id}
    )
    
    db.delete(role)
    db.commit()
    return {"message": "删除成功"}


@router.put("/roles/{role_id}/menus")
async def assign_menus(
    role_id: int,
    menu_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign menus to role"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # Clear existing
    db.execute(
        text("DELETE FROM sys_role_menu WHERE role_id = :role_id"),
        {"role_id": role_id}
    )
    
    # Add new
    for menu_id in menu_ids:
        db.execute(
            text("INSERT INTO sys_role_menu (role_id, menu_id) VALUES (:role_id, :menu_id)"),
            {"role_id": role_id, "menu_id": menu_id}
        )
    
    db.commit()
    return {"message": "分配成功"}


@router.get("/roles/{role_id}/menus")
async def get_role_menus(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get role's menu ids"""
    result = db.execute(
        text("SELECT menu_id FROM sys_role_menu WHERE role_id = :role_id"),
        {"role_id": role_id}
    ).fetchall()
    return [r[0] for r in result]


# ============ Menu Management ============

@router.get("/menus", response_model=List[MenuResponse])
async def list_menus(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all menus as tree"""
    menus = db.query(Menu).order_by(Menu.sort).all()
    
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


@router.post("/menus", response_model=MenuResponse)
async def create_menu(
    data: MenuCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create menu"""
    menu = Menu(**data.model_dump())
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return MenuResponse(
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
        children=[]
    )


@router.delete("/menus/{menu_id}")
async def delete_menu(
    menu_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete menu"""
    menu = db.query(Menu).filter(Menu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")
    
    # Check for children
    if db.query(Menu).filter(Menu.parent_id == menu_id).first():
        raise HTTPException(status_code=400, detail="请先删除子菜单")
    
    # Delete role associations
    db.execute(
        text("DELETE FROM sys_role_menu WHERE menu_id = :menu_id"),
        {"menu_id": menu_id}
    )
    
    db.delete(menu)
    db.commit()
    return {"message": "删除成功"}
