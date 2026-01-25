from sqlalchemy import Column, BigInteger, String, DateTime, SmallInteger
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "sys_user"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50))
    email = Column(String(100))
    phone = Column(String(20))
    status = Column(SmallInteger, default=1)  # 1: enabled, 0: disabled
    create_time = Column(DateTime, server_default=func.now())
