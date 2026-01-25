from sqlalchemy import Column, BigInteger, String, Integer, SmallInteger, Table
from app.core.database import Base

# Role-Menu association table (without foreign keys due to DB permission restrictions)
sys_role_menu = Table(
    'sys_role_menu',
    Base.metadata,
    Column('role_id', BigInteger, primary_key=True),
    Column('menu_id', BigInteger, primary_key=True)
)


class Menu(Base):
    __tablename__ = "sys_menu"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    parent_id = Column(BigInteger, default=0)
    title = Column(String(50), nullable=False)
    path = Column(String(200))
    component = Column(String(200))
    icon = Column(String(50))
    sort = Column(Integer, default=0)
    menu_type = Column(SmallInteger)  # 1: directory, 2: menu, 3: button
    permission = Column(String(100))
    status = Column(SmallInteger, default=1)
