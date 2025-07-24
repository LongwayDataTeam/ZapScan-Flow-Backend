from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
import os
import tempfile
from app.core.database import get_db
from app.core.config import settings
from app.schemas.order import (
    OrderCreate, OrderUpdate, OrderResponse, OrderSearch, OrderListResponse,
    OrderUploadResponse, MultiSkuOrderResponse
)
from app.services.order_service import OrderService

router = APIRouter()


@router.post("/", response_model=OrderResponse)
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db)
):
    """Create a new order"""
    return OrderService.create_order(db, order)


@router.get("/", response_model=OrderListResponse)
def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    shipment_tracker: Optional[str] = Query(None),
    order_id: Optional[str] = Query(None),
    channel_id: Optional[str] = Query(None),
    channel_name: Optional[str] = Query(None),
    fulfillment_status: Optional[str] = Query(None),
    buyer_city: Optional[str] = Query(None),
    buyer_state: Optional[str] = Query(None),
    is_multi_sku: Optional[bool] = Query(None),
    is_multi_quantity: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """Get orders with pagination and search filters"""
    search = OrderSearch(
        shipment_tracker=shipment_tracker,
        order_id=order_id,
        channel_id=channel_id,
        channel_name=channel_name,
        fulfillment_status=fulfillment_status,
        buyer_city=buyer_city,
        buyer_state=buyer_state,
        is_multi_sku=is_multi_sku,
        is_multi_quantity=is_multi_quantity
    )
    
    orders = OrderService.get_orders(db, skip=skip, limit=limit, search=search)
    total = OrderService.count_orders(db, search=search)
    
    return OrderListResponse(
        items=orders,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get order by ID"""
    order = OrderService.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/tracker/{shipment_tracker}", response_model=OrderResponse)
def get_order_by_tracker(shipment_tracker: str, db: Session = Depends(get_db)):
    """Get order by shipment tracker"""
    order = OrderService.get_order_by_tracker(db, shipment_tracker)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    order: OrderUpdate,
    db: Session = Depends(get_db)
):
    """Update order"""
    updated_order = OrderService.update_order(db, order_id, order)
    if not updated_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return updated_order


@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """Delete order"""
    success = OrderService.delete_order(db, order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order deleted successfully"}


@router.post("/upload", response_model=OrderUploadResponse)
async def upload_orders(
    file: UploadFile = File(...),
    duplicate_handling: str = Query("allow", description="How to handle duplicates: 'skip', 'allow', or 'update'"),
    db: Session = Depends(get_db)
):
    """Upload orders from CSV/Excel file with duplicate handling options"""
    # Validate duplicate handling parameter
    if duplicate_handling not in ["skip", "allow", "update"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid duplicate_handling. Must be 'skip', 'allow', or 'update'"
        )
    
    # Validate file type
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Validate file size
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size too large. Maximum size: {settings.MAX_FILE_SIZE / (1024*1024)}MB"
        )
    
    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # Process the file with duplicate handling
        result = OrderService.bulk_upload_orders(db, temp_file_path, duplicate_handling)
        return result
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.get("/multi-sku/{shipment_tracker}", response_model=MultiSkuOrderResponse)
def get_multi_sku_order(shipment_tracker: str, db: Session = Depends(get_db)):
    """Get multi-SKU order details with scan progress"""
    order_data = OrderService.get_multi_sku_order(db, shipment_tracker)
    if not order_data:
        raise HTTPException(status_code=404, detail="Order not found")
    return order_data


@router.get("/stats/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    stats = OrderService.get_dashboard_stats(db)
    return stats


@router.get("/recent/activity")
def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get recent order activity"""
    from sqlalchemy import desc
    from app.models.order import Order
    
    recent_orders = db.query(Order).order_by(desc(Order.created_at)).limit(limit).all()
    return {"recent_orders": [order.to_dict() for order in recent_orders]} 