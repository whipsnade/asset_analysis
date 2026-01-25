from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class ProcurementItem(BaseModel):
    name: str
    spec: Optional[str] = None
    quantity: Optional[Decimal] = None


class TextAnalyzeRequest(BaseModel):
    content: str


class MatchedInventory(BaseModel):
    id: int
    product_name: str
    category: Optional[str] = None
    spec: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    sale_price: Optional[Decimal] = None
    supplier: Optional[str] = None

    class Config:
        from_attributes = True


class ProcurementDetailResponse(BaseModel):
    id: int
    original_content: Optional[str] = None
    parsed_name: Optional[str] = None
    parsed_spec: Optional[str] = None
    parsed_quantity: Optional[Decimal] = None
    confidence_score: Optional[Decimal] = None
    match_reason: Optional[str] = None
    status: str
    matched_inventory: Optional[MatchedInventory] = None

    class Config:
        from_attributes = True


class ProcurementTaskResponse(BaseModel):
    id: int
    task_name: Optional[str] = None
    input_type: Optional[str] = None
    status: str
    create_time: Optional[datetime] = None
    details: List[ProcurementDetailResponse] = []

    class Config:
        from_attributes = True


class AnalyzeResponse(BaseModel):
    task_id: int
    status: str
    message: str
    details: List[ProcurementDetailResponse] = []
