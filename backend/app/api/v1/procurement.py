from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from io import BytesIO
import pandas as pd
import asyncio
import json
import uuid

from app.core.database import get_db
from app.models.inventory import ProcurementTask, ProcurementDetail, AssetInventory
from app.schemas.procurement import (
    TextAnalyzeRequest, AnalyzeResponse, 
    ProcurementTaskResponse, ProcurementDetailResponse, MatchedInventory
)
from app.services.ai_service import ai_service, log_queues
from app.services.matching_service import matching_service
from app.services.excel_service import excel_service
from app.utils.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/logs/{session_id}")
async def stream_logs(session_id: str):
    """SSE endpoint for streaming AI logs"""
    
    async def event_generator():
        # Create queue if not exists
        if session_id not in log_queues:
            log_queues[session_id] = asyncio.Queue()
        
        queue = log_queues[session_id]
        
        try:
            while True:
                try:
                    # Wait for log message with timeout
                    log_entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(log_entry, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            # Cleanup queue when connection closes
            if session_id in log_queues:
                del log_queues[session_id]
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/analyze-text", response_model=AnalyzeResponse)
async def analyze_text(
    request: TextAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_session_id: Optional[str] = Header(None)
):
    """Analyze text procurement request"""
    # Set session for logging
    if x_session_id:
        ai_service.set_session(x_session_id)
    
    # Create task
    task = ProcurementTask(
        task_name="文本分析任务",
        input_type="text",
        input_content=request.content,
        status="processing",
        create_user_id=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    try:
        # Extract requirements using AI
        requirements = await ai_service.extract_requirements(request.content)
        
        details = []
        for req in requirements:
            req_name = req.get("name", "")
            req_spec = req.get("spec")
            req_quantity = req.get("quantity")
            
            # Match with inventory
            match_result = await matching_service.match_requirement(
                db, req_name, req_spec, req_quantity
            )
            
            # Create detail record
            detail = ProcurementDetail(
                task_id=task.id,
                original_content=f"{req_name} {req_spec or ''} x{req_quantity or 1}",
                parsed_name=req_name,
                parsed_spec=req_spec,
                parsed_quantity=req_quantity,
                matched_asset_id=match_result.get("matched_id"),
                confidence_score=match_result.get("confidence", 0),
                match_reason=match_result.get("reason"),
                status="completed"
            )
            db.add(detail)
            db.commit()
            db.refresh(detail)
            
            # Build response
            matched_inv = None
            if match_result.get("matched_inventory"):
                inv = match_result["matched_inventory"]
                matched_inv = MatchedInventory(
                    id=inv["id"],
                    product_name=inv["product_name"],
                    category=inv.get("category"),
                    spec=inv.get("spec"),
                    quantity=inv.get("quantity"),
                    unit=inv.get("unit"),
                    sale_price=inv.get("sale_price"),
                    supplier=inv.get("supplier")
                )
            
            details.append(ProcurementDetailResponse(
                id=detail.id,
                original_content=detail.original_content,
                parsed_name=detail.parsed_name,
                parsed_spec=detail.parsed_spec,
                parsed_quantity=detail.parsed_quantity,
                confidence_score=detail.confidence_score,
                match_reason=detail.match_reason,
                status=detail.status,
                matched_inventory=matched_inv
            ))
        
        # Update task status
        task.status = "completed"
        db.commit()
        
        return AnalyzeResponse(
            task_id=task.id,
            status="completed",
            message=f"成功解析 {len(details)} 条采购需求",
            details=details
        )
    
    except Exception as e:
        task.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/analyze-file", response_model=AnalyzeResponse)
async def analyze_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_session_id: Optional[str] = Header(None)
):
    """Analyze single Excel procurement request (backward compatible)"""
    # Delegate to multi-file handler
    return await analyze_files(
        files=[file],
        db=db,
        current_user=current_user,
        x_session_id=x_session_id
    )


@router.post("/analyze-files", response_model=AnalyzeResponse)
async def analyze_files(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_session_id: Optional[str] = Header(None)
):
    """Analyze multiple Excel procurement requests and merge results"""
    # Set session for logging
    if x_session_id:
        ai_service.set_session(x_session_id)
    
    # Validate files
    file_names = []
    for file in files:
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail=f"文件 {file.filename} 格式不支持，请上传Excel文件(.xlsx或.xls)")
        file_names.append(file.filename)
    
    # Create task
    task = ProcurementTask(
        task_name=f"文件分析: {', '.join(file_names[:3])}{'...' if len(file_names) > 3 else ''} ({len(files)}个文件)",
        input_type="excel",
        file_path=", ".join(file_names),
        status="processing",
        create_user_id=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    try:
        # Parse all files and merge requirements
        all_requirements = []
        for file in files:
            content = await file.read()
            requirements = excel_service.parse_procurement_excel(BytesIO(content))
            # Add file source info
            for req in requirements:
                req['_source_file'] = file.filename
            all_requirements.extend(requirements)
        
        details = []
        for req in all_requirements:
            req_name = req.get("name", "")
            req_spec = req.get("spec")
            req_quantity = req.get("quantity")
            source_file = req.get("_source_file", "")
            
            # Match with inventory
            match_result = await matching_service.match_requirement(
                db, req_name, req_spec, req_quantity
            )
            
            # Create detail record
            detail = ProcurementDetail(
                task_id=task.id,
                original_content=f"{req_name} {req_spec or ''} x{req_quantity or 1}",
                parsed_name=req_name,
                parsed_spec=req_spec,
                parsed_quantity=req_quantity,
                matched_asset_id=match_result.get("matched_id"),
                confidence_score=match_result.get("confidence", 0),
                match_reason=match_result.get("reason"),
                status="completed"
            )
            db.add(detail)
            db.commit()
            db.refresh(detail)
            
            # Build response
            matched_inv = None
            if match_result.get("matched_inventory"):
                inv = match_result["matched_inventory"]
                matched_inv = MatchedInventory(
                    id=inv["id"],
                    product_name=inv["product_name"],
                    category=inv.get("category"),
                    spec=inv.get("spec"),
                    quantity=inv.get("quantity"),
                    unit=inv.get("unit"),
                    sale_price=inv.get("sale_price"),
                    supplier=inv.get("supplier")
                )
            
            details.append(ProcurementDetailResponse(
                id=detail.id,
                original_content=detail.original_content,
                parsed_name=detail.parsed_name,
                parsed_spec=detail.parsed_spec,
                parsed_quantity=detail.parsed_quantity,
                confidence_score=detail.confidence_score,
                match_reason=detail.match_reason,
                status=detail.status,
                matched_inventory=matched_inv
            ))
        
        # Update task status
        task.status = "completed"
        db.commit()
        
        return AnalyzeResponse(
            task_id=task.id,
            status="completed",
            message=f"成功解析 {len(details)} 条采购需求 (来自{len(files)}个文件)",
            details=details
        )
    
    except Exception as e:
        task.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/tasks", response_model=List[ProcurementTaskResponse])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List procurement analysis tasks"""
    tasks = db.query(ProcurementTask).filter(
        ProcurementTask.create_user_id == current_user.id
    ).order_by(ProcurementTask.id.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    result = []
    for task in tasks:
        result.append(ProcurementTaskResponse(
            id=task.id,
            task_name=task.task_name,
            input_type=task.input_type,
            status=task.status,
            create_time=task.create_time,
            details=[]
        ))
    
    return result


@router.get("/tasks/{task_id}", response_model=ProcurementTaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task details with matching results"""
    task = db.query(ProcurementTask).filter(
        ProcurementTask.id == task_id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # Get details
    details_db = db.query(ProcurementDetail).filter(
        ProcurementDetail.task_id == task_id
    ).all()
    
    details = []
    for d in details_db:
        matched_inv = None
        if d.matched_asset_id:
            inv = db.query(AssetInventory).filter(
                AssetInventory.id == d.matched_asset_id
            ).first()
            if inv:
                matched_inv = MatchedInventory(
                    id=inv.id,
                    product_name=inv.product_name,
                    category=inv.category,
                    spec=inv.spec,
                    quantity=inv.quantity,
                    unit=inv.unit,
                    sale_price=inv.sale_price,
                    supplier=inv.supplier
                )
        
        details.append(ProcurementDetailResponse(
            id=d.id,
            original_content=d.original_content,
            parsed_name=d.parsed_name,
            parsed_spec=d.parsed_spec,
            parsed_quantity=d.parsed_quantity,
            confidence_score=d.confidence_score,
            match_reason=d.match_reason,
            status=d.status,
            matched_inventory=matched_inv
        ))
    
    return ProcurementTaskResponse(
        id=task.id,
        task_name=task.task_name,
        input_type=task.input_type,
        status=task.status,
        create_time=task.create_time,
        details=details
    )


@router.post("/export")
async def export_analysis_result(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export analysis results to Excel
    Expected data format:
    {
        "customer_abbr": "客户名称缩写",
        "project_name": "项目/门店名称",
        "invoice_title": "我方开票抬头",
        "requester": "需求发起人",
        "order_date": "采购应下单日期",
        "delivery_address": "收货地址",
        "details": [
            {
                "parsed_name": "产品名称",
                "parsed_spec": "规格",
                "parsed_quantity": 1,
                "matched_inventory": {...},
                "remark": "补充说明",
                "purchase_link": "网购链接"
            }
        ]
    }
    """
    try:
        # Extract common fields
        customer_abbr = data.get("customer_abbr", "")
        project_name = data.get("project_name", "")
        invoice_title = data.get("invoice_title", "")
        requester = data.get("requester", "")
        order_date = data.get("order_date", "")
        delivery_address = data.get("delivery_address", "")
        details = data.get("details", [])
        
        # Build Excel data
        rows = []
        for item in details:
            matched_inv = item.get("matched_inventory") or {}
            
            row = {
                "客户名称缩写": customer_abbr,
                "项目/门店名称": project_name,
                "我方开票抬头": invoice_title,
                "需求发起人": requester,
                "采购应下单日期": order_date,
                "货品编码": str(matched_inv.get("id", "")) if matched_inv.get("id") else "",
                "合同产品名称": matched_inv.get("product_name", "") or item.get("parsed_name", ""),
                "合同型号规格": matched_inv.get("spec", "") or item.get("parsed_spec", ""),
                "合同数量": item.get("parsed_quantity", ""),
                "单位": matched_inv.get("unit", ""),
                "合同单价": matched_inv.get("sale_price", ""),
                "采购需求补充说明": item.get("remark", ""),
                "网购链接": item.get("purchase_link", ""),
                "收货地址": delivery_address
            }
            rows.append(row)
        
        # Create DataFrame
        columns = [
            "客户名称缩写", "项目/门店名称", "我方开票抬头", "需求发起人",
            "采购应下单日期", "货品编码", "合同产品名称", "合同型号规格",
            "合同数量", "单位", "合同单价", "采购需求补充说明", "网购链接", "收货地址"
        ]
        
        df = pd.DataFrame(rows, columns=columns)
        
        # Fill NaN with empty string
        df = df.fillna("")
        
        # Write to Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='采购清单')
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=procurement_result.xlsx"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")
