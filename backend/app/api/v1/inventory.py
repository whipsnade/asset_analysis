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
    """
    Import inventory from Excel file
    根据 产品名称+设备分类+型号规格 去重：
    - 已存在则更新：数量、销售单价、采购单价、供应商
    - 不存在则新增
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传Excel文件(.xlsx或.xls)")
    
    try:
        content = await file.read()
        records = excel_service.parse_inventory_excel(BytesIO(content))
        
        imported_count = 0
        updated_count = 0
        
        for record in records:
            # Clean record data
            clean_record = {}
            for key, value in record.items():
                if key in ['product_name', 'category', 'category_alias', 'spec', 'unit', 
                          'contract_remark', 'purchase_remark', 'supplier']:
                    clean_record[key] = str(value).strip() if value and str(value) != 'nan' else None
                elif key in ['quantity', 'sale_price', 'sale_total', 'purchase_price']:
                    try:
                        if value is None or (isinstance(value, float) and str(value) == 'nan'):
                            clean_record[key] = None
                        else:
                            clean_record[key] = float(value)
                    except:
                        clean_record[key] = None
            
            if not clean_record.get('product_name'):
                continue
            
            # 根据 产品名称+设备分类+型号规格 查找已存在的记录
            product_name = clean_record.get('product_name')
            category = clean_record.get('category') or ''
            spec = clean_record.get('spec') or ''
            
            existing = db.query(AssetInventory).filter(
                AssetInventory.product_name == product_name,
                (AssetInventory.category == category) | 
                ((AssetInventory.category == None) & (category == '')),
                (AssetInventory.spec == spec) |
                ((AssetInventory.spec == None) & (spec == ''))
            ).first()
            
            if existing:
                # 更新已存在的记录
                if clean_record.get('quantity') is not None:
                    existing.quantity = clean_record['quantity']
                if clean_record.get('sale_price') is not None:
                    existing.sale_price = clean_record['sale_price']
                if clean_record.get('purchase_price') is not None:
                    existing.purchase_price = clean_record['purchase_price']
                if clean_record.get('supplier'):
                    existing.supplier = clean_record['supplier']
                # 也更新分类别名（如果有）
                if clean_record.get('category_alias'):
                    existing.category_alias = clean_record['category_alias']
                updated_count += 1
            else:
                # 新增记录
                item = AssetInventory(**clean_record)
                db.add(item)
                imported_count += 1
        
        db.commit()
        
        message_parts = []
        if imported_count > 0:
            message_parts.append(f"新增 {imported_count} 条")
        if updated_count > 0:
            message_parts.append(f"更新 {updated_count} 条")
        
        message = "成功" + "，".join(message_parts) + "记录" if message_parts else "没有需要导入的数据"
        
        return {
            "message": message, 
            "imported": imported_count, 
            "updated": updated_count
        }
    
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
