from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.order import Order
from app.models.scan import ScanCheckpoint
from app.models.product import Product

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    try:
        # Get total orders
        total_orders = db.query(Order).count()
        
        # Get orders by status
        pending_orders = db.query(Order).filter(Order.fulfillment_status == "pending").count()
        completed_orders = db.query(Order).filter(Order.fulfillment_status == "completed").count()
        processing_orders = db.query(Order).filter(Order.fulfillment_status == "processing").count()
        
        # Get total scans
        total_scans = db.query(ScanCheckpoint).count()
        
        # Get scans by type
        label_scans = db.query(ScanCheckpoint).filter(ScanCheckpoint.scan_type == "label").count()
        packing_scans = db.query(ScanCheckpoint).filter(ScanCheckpoint.scan_type == "packing").count()
        dispatch_scans = db.query(ScanCheckpoint).filter(ScanCheckpoint.scan_type == "dispatch").count()
        
        # Get total products
        total_products = db.query(Product).count()
        active_products = db.query(Product).filter(Product.is_active == 1).count()
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recent_orders = db.query(Order).filter(Order.created_at >= yesterday).count()
        recent_scans = db.query(ScanCheckpoint).filter(ScanCheckpoint.created_at >= yesterday).count()
        
        return {
            "orders": {
                "total": total_orders,
                "pending": pending_orders,
                "processing": processing_orders,
                "completed": completed_orders,
                "recent_24h": recent_orders
            },
            "scans": {
                "total": total_scans,
                "label": label_scans,
                "packing": packing_scans,
                "dispatch": dispatch_scans,
                "recent_24h": recent_scans
            },
            "products": {
                "total": total_products,
                "active": active_products
            },
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard stats: {str(e)}") 