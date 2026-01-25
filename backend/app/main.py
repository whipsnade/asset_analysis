from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.security import get_password_hash
from app.api.v1 import auth, inventory, procurement, system
from app.models.user import User
from app.models.role import Role
from app.models.menu import Menu
from app.models.inventory import AssetInventory, ProcurementTask, ProcurementDetail


def init_db():
    """Initialize database tables and default data"""
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Create admin role if not exists
        admin_role = db.query(Role).filter(Role.role_key == "admin").first()
        if not admin_role:
            admin_role = Role(role_name="超级管理员", role_key="admin")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
        
        # Create common role if not exists
        common_role = db.query(Role).filter(Role.role_key == "common").first()
        if not common_role:
            common_role = Role(role_name="普通用户", role_key="common")
            db.add(common_role)
            db.commit()
        
        # Create admin user if not exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                nickname="超级管理员"
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            # Assign admin role
            from sqlalchemy import text
            db.execute(
                text("INSERT INTO sys_user_role (user_id, role_id) VALUES (:user_id, :role_id)"),
                {"user_id": admin_user.id, "role_id": admin_role.id}
            )
            db.commit()
        
        # Create default menus if not exists
        if db.query(Menu).count() == 0:
            menus = [
                Menu(id=1, parent_id=0, title="工作台", path="/dashboard", component="dashboard/index", icon="Odometer", sort=1, menu_type=2),
                Menu(id=2, parent_id=0, title="库存管理", path="/inventory", component="inventory/index", icon="Box", sort=2, menu_type=2, permission="inventory:list"),
                Menu(id=3, parent_id=0, title="采购分析", path="/procurement", component="procurement/index", icon="DataAnalysis", sort=3, menu_type=2, permission="procurement:analyze"),
                Menu(id=4, parent_id=0, title="系统管理", path="/system", component="", icon="Setting", sort=4, menu_type=1),
                Menu(id=5, parent_id=4, title="用户管理", path="/system/users", component="system/users", icon="User", sort=1, menu_type=2, permission="system:user:list"),
                Menu(id=6, parent_id=4, title="角色管理", path="/system/roles", component="system/roles", icon="UserFilled", sort=2, menu_type=2, permission="system:role:list"),
                Menu(id=7, parent_id=4, title="菜单管理", path="/system/menus", component="system/menus", icon="Menu", sort=3, menu_type=2, permission="system:menu:list"),
            ]
            for menu in menus:
                db.add(menu)
            db.commit()
            
            # Assign all menus to admin role
            for menu in menus:
                db.execute(
                    text("INSERT INTO sys_role_menu (role_id, menu_id) VALUES (:role_id, :menu_id)"),
                    {"role_id": admin_role.id, "menu_id": menu.id}
                )
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["认证"])
app.include_router(inventory.router, prefix=f"{settings.API_V1_STR}/inventory", tags=["库存管理"])
app.include_router(procurement.router, prefix=f"{settings.API_V1_STR}/procurement", tags=["采购分析"])
app.include_router(system.router, prefix=f"{settings.API_V1_STR}/system", tags=["系统管理"])

# Mount static files for frontend (if exists)
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "智能采购管理系统运行中"}
