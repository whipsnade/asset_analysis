from sqlalchemy import Column, BigInteger, String, DateTime, SmallInteger, Table
from sqlalchemy.sql import func
from app.core.database import Base

# User-Role association table (without foreign keys due to DB permission restrictions)
sys_user_role = Table(
    'sys_user_role',
    Base.metadata,
    Column('user_id', BigInteger, primary_key=True),
    Column('role_id', BigInteger, primary_key=True)
)


class Role(Base):
    __tablename__ = "sys_role"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    role_name = Column(String(50), nullable=False)
    role_key = Column(String(50), unique=True, nullable=False)
    status = Column(SmallInteger, default=1)
    create_time = Column(DateTime, server_default=func.now())
