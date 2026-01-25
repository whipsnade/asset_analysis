from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class InventoryBase(BaseModel):
    product_name: str
    category: Optional[str] = None
    spec: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    sale_price: Optional[Decimal] = None
    sale_total: Optional[Decimal] = None
    contract_remark: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    purchase_remark: Optional[str] = None
    supplier: Optional[str] = None


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    product_name: Optional[str] = None
    category: Optional[str] = None
    spec: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    sale_price: Optional[Decimal] = None
    sale_total: Optional[Decimal] = None
    contract_remark: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    purchase_remark: Optional[str] = None
    supplier: Optional[str] = None


class InventoryResponse(InventoryBase):
    id: int
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class InventoryListResponse(BaseModel):
    items: List[InventoryResponse]
    total: int
    page: int
    page_size: int
