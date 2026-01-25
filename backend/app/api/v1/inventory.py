from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from io import BytesIO

from app.core.database import get_db
from app.models.inventory import AssetInventory
from app.schemas.inventory import (
    InventoryCreate, InventoryUpdate, InventoryResponse, InventoryListResponse
)
from app.services.excel_service import excel_service
from app.utils.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("", response_model=InventoryListResponse)
async def list_inventory(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List inventory with pagination"""
    query = db.query(AssetInventory)
    
    if keyword:
        query = query.filter(
            AssetInventory.product_name.like(f"%{keyword}%") |
            AssetInventory.spec.like(f"%{keyword}%")
        )
    
    if category:
        query = query.filter(AssetInventory.category == category)
    
    total = query.count()
    items = query.order_by(AssetInventory.id.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return InventoryListResponse(
        items=[InventoryResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/categories")
async def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all categories"""
    result = db.execute(
        text("SELECT DISTINCT category FROM asset_inventory WHERE category IS NOT NULL AND category != ''")
    ).fetchall()
    return [r[0] for r in result]


@router.get("/{id}", response_model=InventoryResponse)
async def get_inventory(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get inventory by ID"""
    item = db.query(AssetInventory).filter(AssetInventory.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="库存记录不存在")
    return InventoryResponse.model_validate(item)


@router.post("", response_model=InventoryResponse)
async def create_inventory(
    data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new inventory record"""
    item = AssetInventory(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return InventoryResponse.model_validate(item)


@router.put("/{id}", response_model=InventoryResponse)
async def update_inventory(
    id: int,
    data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update inventory record"""
    item = db.query(AssetInventory).filter(AssetInventory.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="库存记录不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    
    db.commit()
    db.refresh(item)
    return InventoryResponse.model_validate(item)


@router.delete("/{id}")
async def delete_inventory(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete inventory record"""
    item = db.query(AssetInventory).filter(AssetInventory.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="库存记录不存在")
    
    db.delete(item)
    db.commit()
    return {"message": "删除成功"}


@router.post("/import")
async def import_inventory(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Import inventory from Excel file"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传Excel文件(.xlsx或.xls)")
    
    try:
        content = await file.read()
        records = excel_service.parse_inventory_excel(BytesIO(content))
        
        imported_count = 0
        for record in records:
            # Clean record data
            clean_record = {}
            for key, value in record.items():
                if key in ['product_name', 'category', 'spec', 'unit', 
                          'contract_remark', 'purchase_remark', 'supplier']:
                    clean_record[key] = str(value) if value and str(value) != 'nan' else None
                elif key in ['quantity', 'sale_price', 'sale_total', 'purchase_price']:
                    try:
                        if value is None or (isinstance(value, float) and str(value) == 'nan'):
                            clean_record[key] = None
                        else:
                            clean_record[key] = float(value)
                    except:
                        clean_record[key] = None
            
            if clean_record.get('product_name'):
                item = AssetInventory(**clean_record)
                db.add(item)
                imported_count += 1
        
        db.commit()
        return {"message": f"成功导入 {imported_count} 条记录", "count": imported_count}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")


@router.get("/export/template")
async def export_template(
    current_user: User = Depends(get_current_user)
):
    """Export inventory template"""
    output = excel_service.generate_inventory_template()
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=inventory_template.xlsx"}
    )
