from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.core.database import get_db
from app.models.scan import ScanCheckpoint, ScanSession
from app.models.order import Order, OrderItem
from app.schemas.scan import (
    LabelScanCreate, PackingScanCreate, DispatchScanCreate,
    ScanResponse, ScanValidationResponse, ScanStatusResponse, ScanHistoryResponse,
    ScanSessionCreate, ScanSessionResponse
)
from app.services.scan_service import ScanService

router = APIRouter()


@router.post("/label/{shipment_tracker}", response_model=ScanResponse)
def scan_label(
    shipment_tracker: str,
    scan_data: LabelScanCreate,
    db: Session = Depends(get_db)
):
    """Process label checkpoint scan"""
    try:
        scan_checkpoint = ScanService.process_label_scan(db, scan_data)
        return scan_checkpoint
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan processing error: {str(e)}")


@router.post("/packing/{shipment_tracker}", response_model=ScanResponse)
def scan_packing(
    shipment_tracker: str,
    scan_data: PackingScanCreate,
    db: Session = Depends(get_db)
):
    """Process packing checkpoint scan"""
    try:
        scan_checkpoint = ScanService.process_packing_scan(db, scan_data)
        return scan_checkpoint
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan processing error: {str(e)}")


@router.post("/packing/item/{shipment_tracker}", response_model=ScanResponse)
def scan_packing_item(
    shipment_tracker: str,
    scan_data: PackingScanCreate,
    db: Session = Depends(get_db)
):
    """Process individual item scan at packing checkpoint"""
    try:
        scan_checkpoint = ScanService.process_packing_scan(db, scan_data)
        return scan_checkpoint
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan processing error: {str(e)}")


@router.post("/dispatch/{shipment_tracker}", response_model=ScanResponse)
def scan_dispatch(
    shipment_tracker: str,
    scan_data: DispatchScanCreate,
    db: Session = Depends(get_db)
):
    """Process dispatch checkpoint scan"""
    try:
        scan_checkpoint = ScanService.process_dispatch_scan_multi_sku(db, scan_data)
        return scan_checkpoint
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan processing error: {str(e)}")


@router.post("/label/", response_model=ScanResponse)
def scan_label_multi_sku(
    scan_data: LabelScanCreate,
    db: Session = Depends(get_db)
):
    """Process label checkpoint scan with Multi-SKU support"""
    try:
        # Extract tracker code from request body
        tracker_code = scan_data.tracker_code
        
        # Get all orders with this tracking ID
        orders = db.query(Order).filter(Order.tracker_code == tracker_code).all()
        if not orders:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Count total SKUs for this tracking ID
        total_skus = len(orders)
        
        # Get already scanned SKUs for this tracking ID
        scanned_orders = db.query(ScanCheckpoint).join(Order).filter(
            Order.tracker_code == tracker_code,
            ScanCheckpoint.checkpoint_type == "label"
        ).all()
        
        scanned_order_ids = [scan.order_id for scan in scanned_orders]
        
        # Get remaining unscanned SKUs
        remaining_orders = [order for order in orders if order.id not in scanned_order_ids]
        
        if not remaining_orders:
            raise HTTPException(status_code=400, detail="All SKUs for this tracking ID have already been scanned")
        
        # Select the next SKU in ascending order by channel_id (or order_id if channel_id is null)
        selected_order = min(remaining_orders, key=lambda x: (x.channel_id or '', x.order_id))
        
        # Get the first order item for SKU details
        selected_order_item = db.query(OrderItem).filter(OrderItem.order_id == selected_order.id).first()
        
        # Update scan data to use the selected order
        scan_data.order_id = selected_order.id
        scan_data.tracker_code = tracker_code
        
        # Process the scan
        scan_checkpoint = ScanService.process_label_scan_multi_sku(db, scan_data)
        
        # Add Multi-SKU information to response
        # Count scanned SKUs AFTER processing this scan
        new_scanned_count = len(scanned_order_ids) + 1
        new_remaining_count = total_skus - new_scanned_count
        
        response_data = scan_checkpoint.dict()
        response_data.update({
            "is_multi_sku": total_skus > 1,
            "total_sku_count": total_skus,
            "scanned_sku_count": new_scanned_count,
            "remaining_sku_count": new_remaining_count,
            "selected_sku_g_code": selected_order_item.g_code if selected_order_item else None,
            "selected_sku_ean_code": selected_order_item.ean_code if selected_order_item else None,
            "selected_sku_product_code": selected_order_item.product_sku_code if selected_order_item else None
        })
        
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan processing error: {str(e)}")


@router.post("/packing/dual/", response_model=ScanResponse)
def scan_packing_dual_multi_sku(
    scan_data: PackingScanCreate,
    db: Session = Depends(get_db)
):
    """Process dual packing scan with Multi-SKU support"""
    try:
        # Extract tracker code and product code from request body
        tracker_code = scan_data.tracker_code
        product_code = scan_data.product_code
        
        # Get all orders with this tracking ID
        orders = db.query(Order).filter(Order.tracker_code == tracker_code).all()
        if not orders:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Count total SKUs for this tracking ID
        total_skus = len(orders)
        
        # Get already scanned SKUs for this tracking ID
        scanned_orders = db.query(ScanCheckpoint).join(Order).filter(
            Order.tracker_code == tracker_code,
            ScanCheckpoint.checkpoint_type == "packing"
        ).all()
        
        scanned_order_ids = [scan.order_id for scan in scanned_orders]
        
        # Get remaining unscanned SKUs
        remaining_orders = [order for order in orders if order.id not in scanned_order_ids]
        
        if not remaining_orders:
            raise HTTPException(status_code=400, detail="All SKUs for this tracking ID have already been scanned")
        
        # Select SKUs in ascending order by channel ID
        selected_order = min(remaining_orders, key=lambda x: (x.channel_id or '', x.order_id))
        
        # Get the first order item for SKU details
        selected_order_item = db.query(OrderItem).filter(OrderItem.order_id == selected_order.id).first()
        
        # Update scan data to use the selected order
        scan_data.order_id = selected_order.id
        scan_data.tracker_code = tracker_code
        scan_data.product_code = product_code
        
        # Process the scan
        scan_checkpoint = ScanService.process_packing_scan_multi_sku(db, scan_data)
        
        # Add Multi-SKU information to response
        # Count scanned SKUs AFTER processing this scan
        new_scanned_count = len(scanned_order_ids) + 1
        new_remaining_count = total_skus - new_scanned_count
        
        response_data = scan_checkpoint.dict()
        response_data.update({
            "is_multi_sku": total_skus > 1,
            "total_sku_count": total_skus,
            "scanned_sku_count": new_scanned_count,
            "remaining_sku_count": new_remaining_count,
            "selected_sku_g_code": selected_order_item.g_code if selected_order_item else None,
            "selected_sku_ean_code": selected_order_item.ean_code if selected_order_item else None,
            "selected_sku_product_code": selected_order_item.product_sku_code if selected_order_item else None
        })
        
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan processing error: {str(e)}")


@router.post("/dispatch/", response_model=ScanResponse)
def scan_dispatch_multi_sku(
    scan_data: DispatchScanCreate,
    db: Session = Depends(get_db)
):
    """Process dispatch scan with Multi-SKU support"""
    try:
        # Extract tracker code from request body
        tracker_code = scan_data.tracker_code
        
        # Get all orders with this tracking ID
        orders = db.query(Order).filter(Order.tracker_code == tracker_code).all()
        if not orders:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Count total SKUs for this tracking ID
        total_skus = len(orders)
        
        # Get already scanned SKUs for this tracking ID
        scanned_orders = db.query(ScanCheckpoint).join(Order).filter(
            Order.tracker_code == tracker_code,
            ScanCheckpoint.checkpoint_type == "dispatch"
        ).all()
        
        scanned_order_ids = [scan.order_id for scan in scanned_orders]
        
        # Get remaining unscanned SKUs
        remaining_orders = [order for order in orders if order.id not in scanned_order_ids]
        
        if not remaining_orders:
            raise HTTPException(status_code=400, detail="All SKUs for this tracking ID have already been scanned")
        
        # Select SKUs in ascending order by channel ID
        selected_order = min(remaining_orders, key=lambda x: (x.channel_id or '', x.order_id))
        
        # Get the first order item for SKU details
        selected_order_item = db.query(OrderItem).filter(OrderItem.order_id == selected_order.id).first()
        
        # Update scan data to use the selected order
        scan_data.order_id = selected_order.id
        scan_data.tracker_code = tracker_code
        
        # Process the scan
        scan_checkpoint = ScanService.process_dispatch_scan_multi_sku(db, scan_data)
        
        # Add Multi-SKU information to response
        # Count scanned SKUs AFTER processing this scan
        new_scanned_count = len(scanned_order_ids) + 1
        new_remaining_count = total_skus - new_scanned_count
        
        response_data = scan_checkpoint.dict()
        response_data.update({
            "is_multi_sku": total_skus > 1,
            "total_sku_count": total_skus,
            "scanned_sku_count": new_scanned_count,
            "remaining_sku_count": new_remaining_count,
            "selected_sku_g_code": selected_order_item.g_code if selected_order_item else None,
            "selected_sku_ean_code": selected_order_item.ean_code if selected_order_item else None,
            "selected_sku_product_code": selected_order_item.product_sku_code if selected_order_item else None
        })
        
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan processing error: {str(e)}")


@router.get("/validate/g-code/{g_code}", response_model=ScanValidationResponse)
def validate_g_code(g_code: str, db: Session = Depends(get_db)):
    """Validate a G-code scan"""
    return ScanService.validate_g_code(db, g_code)


@router.get("/validate/tracker/{shipment_tracker}", response_model=ScanValidationResponse)
def validate_shipment_tracker(shipment_tracker: str, db: Session = Depends(get_db)):
    """Validate a shipment tracker scan"""
    return ScanService.validate_shipment_tracker(db, shipment_tracker)


@router.get("/status/{shipment_tracker}", response_model=ScanStatusResponse)
def get_scan_status(shipment_tracker: str, db: Session = Depends(get_db)):
    """Get scan status for an order"""
    try:
        return ScanService.get_scan_status(db, shipment_tracker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/status/", response_model=ScanStatusResponse)
def get_scan_status_multi_sku(
    scan_data: dict,
    db: Session = Depends(get_db)
):
    """Get scan status for Multi-SKU orders"""
    try:
        tracker_code = scan_data.get("tracker_code")
        if not tracker_code:
            raise HTTPException(status_code=400, detail="Tracker code is required")
        
        # Get all orders with this tracking ID
        orders = db.query(Order).filter(Order.tracker_code == tracker_code).all()
        if not orders:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Count total SKUs
        total_skus = len(orders)
        
        # Count scanned SKUs (assuming we're checking for label scans)
        scanned_skus = db.query(ScanCheckpoint.order_id).join(Order).filter(
            Order.tracker_code == tracker_code,
            ScanCheckpoint.checkpoint_type == "label"
        ).distinct().count()
        
        # Get first order for basic details
        first_order = orders[0]
        
        return {
            "tracker_code": tracker_code,
            "order_id": first_order.order_id,
            "courier": first_order.courier,
            "channel_name": first_order.channel_name,
            "amount": first_order.amount,
            "buyer_city": first_order.buyer_city,
            "buyer_state": first_order.buyer_state,
            "buyer_pincode": first_order.buyer_pincode,
            "payment_mode": first_order.payment_mode,
            "order_status": first_order.order_status,
            "is_multi_sku": total_skus > 1,
            "total_sku_count": total_skus,
            "scanned_sku_count": scanned_skus,
            "remaining_sku_count": total_skus - scanned_skus,
            "current_sku_g_code": first_order.g_code,
            "current_sku_ean_code": first_order.ean_code
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting scan status: {str(e)}")


@router.get("/history/{shipment_tracker}", response_model=ScanHistoryResponse)
def get_scan_history(shipment_tracker: str, db: Session = Depends(get_db)):
    """Get scan history for an order"""
    try:
        return ScanService.get_scan_history(db, shipment_tracker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/session/create", response_model=ScanSessionResponse)
def create_scan_session(
    session_data: ScanSessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new scan session"""
    try:
        scan_session = ScanService.create_scan_session(
            db, 
            session_data.checkpoint_type, 
            session_data.user_id
        )
        return scan_session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session creation error: {str(e)}")


@router.post("/session/{session_id}/end", response_model=ScanSessionResponse)
def end_scan_session(session_id: str, db: Session = Depends(get_db)):
    """End a scan session"""
    try:
        scan_session = ScanService.end_scan_session(db, session_id)
        return scan_session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session end error: {str(e)}")


@router.get("/session/{session_id}", response_model=ScanSessionResponse)
def get_scan_session(session_id: str, db: Session = Depends(get_db)):
    """Get scan session details"""
    
    scan_session = db.query(ScanSession).filter(ScanSession.session_id == session_id).first()
    if not scan_session:
        raise HTTPException(status_code=404, detail="Scan session not found")
    return scan_session


@router.get("/statistics/platform")
def get_platform_statistics(db: Session = Depends(get_db)):
    """Get platform/courier statistics with scan counts"""
    try:
        # Get all orders with their scan status
        orders = db.query(Order).all()
        
        # Group by courier and calculate statistics
        courier_stats = {}
        
        # Group orders by tracking ID to handle Multi-SKU orders
        tracking_id_groups = {}
        for order in orders:
            tracker_code = order.tracker_code
            if tracker_code not in tracking_id_groups:
                tracking_id_groups[tracker_code] = []
            tracking_id_groups[tracker_code].append(order)
        
        for tracker_code, order_group in tracking_id_groups.items():
            # Use the first order to get courier info
            first_order = order_group[0]
            courier = first_order.courier or "Unknown"
            
            if courier not in courier_stats:
                courier_stats[courier] = {
                    "courier": courier,
                    "total": 0,
                    "scanned": 0,
                    "pending": 0
                }
            
            # Count total SKUs for this tracking ID
            total_skus = len(order_group)
            courier_stats[courier]["total"] += total_skus
            
            # Count scanned SKUs for this tracking ID
            scanned_skus = db.query(ScanCheckpoint.order_id).join(Order).filter(
                Order.tracker_code == tracker_code,
                ScanCheckpoint.checkpoint_type == "label"
            ).distinct().count()
            
            courier_stats[courier]["scanned"] += scanned_skus
            courier_stats[courier]["pending"] += (total_skus - scanned_skus)
        
        # Convert to list and sort by total count
        result = list(courier_stats.values())
        result.sort(key=lambda x: x["total"], reverse=True)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching platform statistics: {str(e)}")


@router.get("/recent")
def get_recent_scans(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of records per page"),
    db: Session = Depends(get_db)
):
    """Get recent scans with pagination"""
    try:
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get recent scans with order details
        recent_scans = db.query(ScanCheckpoint, Order).join(
            Order, ScanCheckpoint.order_id == Order.id
        ).order_by(
            desc(ScanCheckpoint.created_at)
        ).offset(offset).limit(limit).all()
        
        # Get total count
        total_count = db.query(ScanCheckpoint).count()
        
        # Format response
        results = []
        for scan_checkpoint, order in recent_scans:
            # Determine last scan type
            last_scan = scan_checkpoint.checkpoint_type.capitalize()
            
            # Determine scan status
            scan_status = "Success" if scan_checkpoint.status == "success" else "Error"
            
            # Determine distribution type
            distribution = "Multi SKU" if order.is_multi_sku else "Single SKU"
            
            # Format scan time
            scan_time = scan_checkpoint.created_at.strftime("%Y-%m-%d %H:%M:%S") if scan_checkpoint.created_at else ""
            
            results.append({
                "id": str(scan_checkpoint.id),
                "tracking_id": order.shipment_tracker,
                "platform": order.courier or "Unknown",
                "last_scan": last_scan,
                "scan_status": scan_status,
                "distribution": distribution,
                "scan_time": scan_time,
                "amount": float(order.total_amount) if order.total_amount else 0,
                "buyer_city": order.buyer_city or "Unknown",
                "courier": order.courier or "Unknown"
            })
        
        return {
            "results": results,
            "count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent scans: {str(e)}")


@router.get("/stats/daily")
def get_daily_scan_stats(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """Get daily scanning statistics"""
    from datetime import datetime, date as date_type
    
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = date_type.today()
    
    # Get scans for the date
    scans = db.query(ScanCheckpoint).filter(
        func.date(ScanCheckpoint.created_at) == target_date
    ).all()
    
    # Calculate statistics
    total_scans = len(scans)
    successful_scans = len([s for s in scans if s.status == "success"])
    failed_scans = len([s for s in scans if s.status == "error"])
    
    label_scans = len([s for s in scans if s.checkpoint_type == "label"])
    packing_scans = len([s for s in scans if s.checkpoint_type == "packing"])
    dispatch_scans = len([s for s in scans if s.checkpoint_type == "dispatch"])
    
    return {
        "date": target_date.isoformat(),
        "total_scans": total_scans,
        "successful_scans": successful_scans,
        "failed_scans": failed_scans,
        "label_scans": label_scans,
        "packing_scans": packing_scans,
        "dispatch_scans": dispatch_scans,
        "success_rate": (successful_scans / total_scans * 100) if total_scans > 0 else 0
    }


@router.get("/errors/recent")
def get_recent_scan_errors(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get recent scan errors"""
    from app.models.scan import ScanCheckpoint
    from sqlalchemy import desc
    
    errors = db.query(ScanCheckpoint).filter(
        ScanCheckpoint.status == "error"
    ).order_by(
        desc(ScanCheckpoint.created_at)
    ).limit(limit).all()
    
    return [error.to_dict() for error in errors] 


@router.get("/count/{tracker_code}")
def get_scan_count_and_progress(
    tracker_code: str,
    db: Session = Depends(get_db)
):
    """Get scan count and progress for a tracking ID"""
    try:
        # Get all orders with this tracking ID
        orders = db.query(Order).filter(Order.tracker_code == tracker_code).all()
        if not orders:
            raise HTTPException(status_code=404, detail="Tracking ID not found")
        
        # Count total SKUs
        total_skus = len(orders)
        
        # Count scanned SKUs for each checkpoint
        label_scanned = db.query(ScanCheckpoint.order_id).join(Order).filter(
            Order.tracker_code == tracker_code,
            ScanCheckpoint.checkpoint_type == "label"
        ).distinct().count()
        
        packing_scanned = db.query(ScanCheckpoint.order_id).join(Order).filter(
            Order.tracker_code == tracker_code,
            ScanCheckpoint.checkpoint_type == "packing"
        ).distinct().count()
        
        dispatch_scanned = db.query(ScanCheckpoint.order_id).join(Order).filter(
            Order.tracker_code == tracker_code,
            ScanCheckpoint.checkpoint_type == "dispatch"
        ).distinct().count()
        
        # Get SKU details in ascending order by channel_id
        sorted_orders = sorted(orders, key=lambda x: (x.channel_id or '', x.order_id))
        
        return {
            "tracker_code": tracker_code,
            "total_sku_count": total_skus,
            "label_scanned": label_scanned,
            "packing_scanned": packing_scanned,
            "dispatch_scanned": dispatch_scanned,
            "label_remaining": total_skus - label_scanned,
            "packing_remaining": total_skus - packing_scanned,
            "dispatch_remaining": total_skus - dispatch_scanned,
            "can_scan_label": label_scanned < total_skus,
            "can_scan_packing": packing_scanned < total_skus,
            "can_scan_dispatch": dispatch_scanned < total_skus,
            "sku_details": [
                {
                    "order_id": order.order_id,
                    "channel_id": order.channel_id,
                    "g_code": order.g_code,
                    "ean_code": order.ean_code,
                    "product_sku_code": order.product_sku_code,
                    "is_scanned_label": order.id in [scan.order_id for scan in db.query(ScanCheckpoint).filter(
                        ScanCheckpoint.order_id == order.id,
                        ScanCheckpoint.checkpoint_type == "label"
                    ).all()],
                    "is_scanned_packing": order.id in [scan.order_id for scan in db.query(ScanCheckpoint).filter(
                        ScanCheckpoint.order_id == order.id,
                        ScanCheckpoint.checkpoint_type == "packing"
                    ).all()],
                    "is_scanned_dispatch": order.id in [scan.order_id for scan in db.query(ScanCheckpoint).filter(
                        ScanCheckpoint.order_id == order.id,
                        ScanCheckpoint.checkpoint_type == "dispatch"
                    ).all()]
                }
                for order in sorted_orders
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting scan count: {str(e)}") 