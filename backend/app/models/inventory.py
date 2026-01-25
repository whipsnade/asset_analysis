from sqlalchemy import Column, BigInteger, String, DateTime, Text, DECIMAL
from sqlalchemy.sql import func
from app.core.database import Base


class AssetInventory(Base):
    __tablename__ = "asset_inventory"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_name = Column(String(200), nullable=False)
    category = Column(String(100))
    spec = Column(String(500))
    quantity = Column(DECIMAL(10, 2))
    unit = Column(String(20))
    sale_price = Column(DECIMAL(12, 2))
    sale_total = Column(DECIMAL(12, 2))
    contract_remark = Column(Text)
    purchase_price = Column(DECIMAL(12, 2))
    purchase_remark = Column(Text)
    supplier = Column(String(100))
    create_time = Column(DateTime, server_default=func.now())
    update_time = Column(DateTime, onupdate=func.now())


class ProcurementTask(Base):
    __tablename__ = "procurement_task"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_name = Column(String(200))
    input_type = Column(String(20))  # excel/text
    input_content = Column(Text)
    file_path = Column(String(500))
    status = Column(String(20), default='pending')  # pending/processing/completed/failed
    create_user_id = Column(BigInteger)
    create_time = Column(DateTime, server_default=func.now())


class ProcurementDetail(Base):
    __tablename__ = "procurement_detail"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, nullable=False)
    original_content = Column(Text)
    parsed_name = Column(String(200))
    parsed_spec = Column(String(500))
    parsed_quantity = Column(DECIMAL(10, 2))
    matched_asset_id = Column(BigInteger)
    confidence_score = Column(DECIMAL(5, 4))
    match_reason = Column(Text)
    status = Column(String(20), default='pending')
    create_time = Column(DateTime, server_default=func.now())
