from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime
import json
from app.models.scan import ScanCheckpoint, ScanSession
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.scan import (
    LabelScanCreate, PackingScanCreate, DispatchScanCreate,
    ScanValidationResponse, ScanStatusResponse, ScanHistoryResponse
)
from app.services.product_service import ProductService


class ScanService:
    
    @staticmethod
    def validate_g_code(db: Session, g_code: str) -> ScanValidationResponse:
        """Validate a G-code scan"""
        product = ProductService.get_product_by_g_code(db, g_code)
        
        if not product:
            return ScanValidationResponse(
                is_valid=False,
                message=f"Invalid G-code: {g_code} not found in product catalog"
            )
        
        return ScanValidationResponse(
            is_valid=True,
            message=f"Valid G-code: {g_code}",
            product_info=product.to_dict()
        )
    
    @staticmethod
    def validate_shipment_tracker(db: Session, shipment_tracker: str) -> ScanValidationResponse:
        """Validate a shipment tracker scan"""
        order = db.query(Order).filter(Order.shipment_tracker == shipment_tracker).first()
        
        if not order:
            return ScanValidationResponse(
                is_valid=False,
                message=f"Invalid shipment tracker: {shipment_tracker} not found"
            )
        
        return ScanValidationResponse(
            is_valid=True,
            message=f"Valid shipment tracker: {shipment_tracker}",
            order_info=order.to_dict()
        )
    
    @staticmethod
    def process_label_scan(db: Session, scan_data: LabelScanCreate) -> ScanCheckpoint:
        """Process label checkpoint scan"""
        # Validate shipment tracker
        order = db.query(Order).filter(Order.shipment_tracker == scan_data.shipment_tracker).first()
        if not order:
            raise ValueError(f"Order with shipment tracker {scan_data.shipment_tracker} not found")
        
        # Check if already scanned
        existing_scan = db.query(ScanCheckpoint).filter(
            and_(
                ScanCheckpoint.order_id == order.id,
                ScanCheckpoint.checkpoint_type == "label"
            )
        ).first()
        
        if existing_scan:
            raise ValueError("Label checkpoint already scanned for this order")
        
        # Create scan record
        scan_checkpoint = ScanCheckpoint(
            order_id=order.id,
            checkpoint_type="label",
            scanned_by=scan_data.scanned_by,
            scan_data=json.dumps({
                "shipment_tracker": scan_data.shipment_tracker,
                "scan_time": datetime.now().isoformat()
            }),
            status="success",
            is_completed=True,
            notes=scan_data.notes
        )
        
        db.add(scan_checkpoint)
        
        # Update order status
        order.fulfillment_status = "label_printed"
        
        db.commit()
        db.refresh(scan_checkpoint)
        return scan_checkpoint
    
    @staticmethod
    def process_label_scan_multi_sku(db: Session, scan_data: LabelScanCreate) -> ScanCheckpoint:
        """Process label checkpoint scan for Multi-SKU orders"""
        # Validate order by ID
        order = db.query(Order).filter(Order.id == scan_data.order_id).first()
        if not order:
            raise ValueError(f"Order with ID {scan_data.order_id} not found")
        
        # Check if already scanned
        existing_scan = db.query(ScanCheckpoint).filter(
            and_(
                ScanCheckpoint.order_id == order.id,
                ScanCheckpoint.checkpoint_type == "label"
            )
        ).first()
        
        if existing_scan:
            raise ValueError("Label checkpoint already scanned for this order")
        
        # Create scan record
        scan_checkpoint = ScanCheckpoint(
            order_id=order.id,
            checkpoint_type="label",
            scanned_by=scan_data.scanned_by,
            scan_data=json.dumps({
                "tracker_code": scan_data.tracker_code,
                "scan_time": datetime.now().isoformat()
            }),
            status="success",
            is_completed=True,
            notes=scan_data.notes
        )
        
        db.add(scan_checkpoint)
        
        # Update order status
        order.fulfillment_status = "label_printed"
        
        db.commit()
        db.refresh(scan_checkpoint)
        return scan_checkpoint
    
    @staticmethod
    def process_packing_scan(db: Session, scan_data: PackingScanCreate) -> ScanCheckpoint:
        """Process packing checkpoint scan"""
        # Validate shipment tracker
        order = db.query(Order).filter(Order.shipment_tracker == scan_data.shipment_tracker).first()
        if not order:
            raise ValueError(f"Order with shipment tracker {scan_data.shipment_tracker} not found")
        
        # Validate G-code
        product = ProductService.get_product_by_g_code(db, scan_data.g_code)
        if not product:
            raise ValueError(f"Invalid G-code: {scan_data.g_code}")
        
        # Check if label is scanned first
        label_scan = db.query(ScanCheckpoint).filter(
            and_(
                ScanCheckpoint.order_id == order.id,
                ScanCheckpoint.checkpoint_type == "label",
                ScanCheckpoint.is_completed == True
            )
        ).first()
        
        if not label_scan:
            raise ValueError("Label checkpoint must be completed before packing scan")
        
        # Check if this item exists in the order
        order_item = db.query(OrderItem).filter(
            and_(
                OrderItem.order_id == order.id,
                OrderItem.g_code == scan_data.g_code
            )
        ).first()
        
        if not order_item:
            raise ValueError(f"G-code {scan_data.g_code} not found in order {scan_data.shipment_tracker}")
        
        # Check if quantity is valid
        if scan_data.quantity_scanned > order_item.quantity:
            raise ValueError(f"Scanned quantity ({scan_data.quantity_scanned}) exceeds order quantity ({order_item.quantity})")
        
        # Check if already scanned
        existing_scan = db.query(ScanCheckpoint).filter(
            and_(
                ScanCheckpoint.order_id == order.id,
                ScanCheckpoint.checkpoint_type == "packing",
                ScanCheckpoint.scan_data.contains(scan_data.g_code)
            )
        ).first()
        
        if existing_scan:
            raise ValueError(f"G-code {scan_data.g_code} already scanned for this order")
        
        # Create scan record
        scan_checkpoint = ScanCheckpoint(
            order_id=order.id,
            checkpoint_type="packing",
            scanned_by=scan_data.scanned_by,
            scan_data=json.dumps({
                "g_code": scan_data.g_code,
                "quantity_scanned": scan_data.quantity_scanned,
                "scan_time": datetime.now().isoformat()
            }),
            status="success",
            is_completed=True,
            notes=scan_data.notes
        )
        
        db.add(scan_checkpoint)
        
        # Update order item status
        order_item.item_status = "scanned"
        
        # Check if all items are scanned
        all_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        scanned_items = db.query(OrderItem).filter(
            and_(
                OrderItem.order_id == order.id,
                OrderItem.item_status == "scanned"
            )
        ).all()
        
        if len(scanned_items) == len(all_items):
            order.fulfillment_status = "packed"
        
        db.commit()
        db.refresh(scan_checkpoint)
        return scan_checkpoint
    
    @staticmethod
    def process_packing_scan_multi_sku(db: Session, scan_data: PackingScanCreate) -> ScanCheckpoint:
        """Process packing checkpoint scan for Multi-SKU orders"""
        # Validate order by ID
        order = db.query(Order).filter(Order.id == scan_data.order_id).first()
        if not order:
            raise ValueError(f"Order with ID {scan_data.order_id} not found")
        
        # Validate G-code
        product = ProductService.get_product_by_g_code(db, scan_data.product_code)
        if not product:
            raise ValueError(f"Invalid product code: {scan_data.product_code}")
        
        # Check if label is scanned first
        label_scan = db.query(ScanCheckpoint).filter(
            and_(
                ScanCheckpoint.order_id == order.id,
                ScanCheckpoint.checkpoint_type == "label",
                ScanCheckpoint.is_completed == True
            )
        ).first()
        
        if not label_scan:
            raise ValueError("Label checkpoint must be completed before packing scan")
        
        # Check if already scanned
        existing_scan = db.query(ScanCheckpoint).filter(
            and_(
                ScanCheckpoint.order_id == order.id,
                ScanCheckpoint.checkpoint_type == "packing"
            )
        ).first()
        
        if existing_scan:
            raise ValueError("Packing checkpoint already scanned for this order")
        
        # Create scan record
        scan_checkpoint = ScanCheckpoint(
            order_id=order.id,
            checkpoint_type="packing",
            scanned_by=scan_data.scanned_by,
            scan_data=json.dumps({
                "tracker_code": scan_data.tracker_code,
                "product_code": scan_data.product_code,
                "scan_time": datetime.now().isoformat()
            }),
            status="success",
            is_completed=True,
            notes=scan_data.notes
        )
        
        db.add(scan_checkpoint)
        
        # Update order status
        order.fulfillment_status = "packed"
        
        db.commit()
        db.refresh(scan_checkpoint)
        return scan_checkpoint
    
    @staticmethod
    def process_dispatch_scan(db: Session, scan_data: DispatchScanCreate) -> ScanCheckpoint:
        """Process dispatch checkpoint scan"""
        # Validate shipment tracker
        order = db.query(Order).filter(Order.shipment_tracker == scan_data.shipment_tracker).first()
        if not order:
            raise ValueError(f"Order with shipment tracker {scan_data.shipment_tracker} not found")
        
        # Check if packing is completed
        packing_scans = db.query(ScanCheckpoint).filter(
            and_(
                ScanCheckpoint.order_id == order.id,
                ScanCheckpoint.checkpoint_type == "packing",
                ScanCheckpoint.is_completed == True
            )
        ).all()
        
        all_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        
        if len(packing_scans) < len(all_items):
            raise ValueError("All items must be scanned at packing checkpoint before dispatch")
        
        # Check if already scanned
        existing_scan = db.query(ScanCheckpoint).filter(
            and_(
                ScanCheckpoint.order_id == order.id,
                ScanCheckpoint.checkpoint_type == "dispatch"
            )
        ).first()
        
        if existing_scan:
            raise ValueError("Dispatch checkpoint already scanned for this order")
        
        # Create scan record
        scan_checkpoint = ScanCheckpoint(
            order_id=order.id,
            checkpoint_type="dispatch",
            scanned_by=scan_data.scanned_by,
            scan_data=json.dumps({
                "shipment_tracker": scan_data.shipment_tracker,
                "scan_time": datetime.now().isoformat()
            }),
            status="success",
            is_completed=True,
            notes=scan_data.notes
        )
        
        db.add(scan_checkpoint)
        
        # Update order status
        order.fulfillment_status = "completed"
        
        # Update all item statuses
        for item in all_items:
            item.item_status = "completed"
        
        db.commit()
        db.refresh(scan_checkpoint)
        return scan_checkpoint
    
    @staticmethod
    def process_dispatch_scan_multi_sku(db: Session, scan_data: DispatchScanCreate) -> ScanCheckpoint:
        """Process dispatch checkpoint scan for Multi-SKU orders"""
        # Validate order by ID
        order = db.query(Order).filter(Order.id == scan_data.order_id).first()
        if not order:
            raise ValueError(f"Order with ID {scan_data.order_id} not found")
        
        # Check if packing is completed
        packing_scan = db.query(ScanCheckpoint).filter(
            and_(
                ScanCheckpoint.order_id == order.id,
                ScanCheckpoint.checkpoint_type == "packing",
                ScanCheckpoint.is_completed == True
            )
        ).first()
        
        if not packing_scan:
            raise ValueError("Packing checkpoint must be completed before dispatch scan")
        
        # Check if already scanned
        existing_scan = db.query(ScanCheckpoint).filter(
            and_(
                ScanCheckpoint.order_id == order.id,
                ScanCheckpoint.checkpoint_type == "dispatch"
            )
        ).first()
        
        if existing_scan:
            raise ValueError("Dispatch checkpoint already scanned for this order")
        
        # Create scan record
        scan_checkpoint = ScanCheckpoint(
            order_id=order.id,
            checkpoint_type="dispatch",
            scanned_by=scan_data.scanned_by,
            scan_data=json.dumps({
                "tracker_code": scan_data.tracker_code,
                "scan_time": datetime.now().isoformat()
            }),
            status="success",
            is_completed=True,
            notes=scan_data.notes
        )
        
        db.add(scan_checkpoint)
        
        # Update order status
        order.fulfillment_status = "dispatched"
        
        db.commit()
        db.refresh(scan_checkpoint)
        return scan_checkpoint
    
    @staticmethod
    def get_scan_status(db: Session, shipment_tracker: str) -> ScanStatusResponse:
        """Get scan status for an order"""
        order = db.query(Order).filter(Order.shipment_tracker == shipment_tracker).first()
        if not order:
            raise ValueError(f"Order with shipment tracker {shipment_tracker} not found")
        
        # Get all scans for this order
        scans = db.query(ScanCheckpoint).filter(ScanCheckpoint.order_id == order.id).all()
        
        label_scan = None
        packing_scans = []
        dispatch_scan = None
        
        for scan in scans:
            if scan.checkpoint_type == "label":
                label_scan = scan
            elif scan.checkpoint_type == "packing":
                packing_scans.append(scan)
            elif scan.checkpoint_type == "dispatch":
                dispatch_scan = scan
        
        # Calculate progress
        total_items = order.total_items
        scanned_items = len(packing_scans)
        progress_percentage = (scanned_items / total_items * 100) if total_items > 0 else 0
        
        return ScanStatusResponse(
            shipment_tracker=shipment_tracker,
            order_id=order.id,
            fulfillment_status=order.fulfillment_status,
            label_scan=label_scan.to_dict() if label_scan else None,
            packing_scans=[scan.to_dict() for scan in packing_scans],
            dispatch_scan=dispatch_scan.to_dict() if dispatch_scan else None,
            is_completed=order.fulfillment_status == "completed",
            progress_percentage=progress_percentage,
            total_items=total_items,
            scanned_items=scanned_items
        )
    
    @staticmethod
    def get_scan_history(db: Session, shipment_tracker: str) -> ScanHistoryResponse:
        """Get scan history for an order"""
        order = db.query(Order).filter(Order.shipment_tracker == shipment_tracker).first()
        if not order:
            raise ValueError(f"Order with shipment tracker {shipment_tracker} not found")
        
        scans = db.query(ScanCheckpoint).filter(ScanCheckpoint.order_id == order.id).all()
        
        successful_scans = len([s for s in scans if s.status == "success"])
        failed_scans = len([s for s in scans if s.status == "error"])
        
        return ScanHistoryResponse(
            shipment_tracker=shipment_tracker,
            scans=[scan.to_dict() for scan in scans],
            total_scans=len(scans),
            successful_scans=successful_scans,
            failed_scans=failed_scans
        )
    
    @staticmethod
    def create_scan_session(db: Session, checkpoint_type: str, user_id: Optional[str] = None) -> ScanSession:
        """Create a new scan session"""
        import uuid
        
        session_id = str(uuid.uuid4())
        scan_session = ScanSession(
            session_id=session_id,
            user_id=user_id,
            checkpoint_type=checkpoint_type
        )
        
        db.add(scan_session)
        db.commit()
        db.refresh(scan_session)
        return scan_session
    
    @staticmethod
    def end_scan_session(db: Session, session_id: str) -> ScanSession:
        """End a scan session"""
        scan_session = db.query(ScanSession).filter(ScanSession.session_id == session_id).first()
        if not scan_session:
            raise ValueError(f"Scan session {session_id} not found")
        
        scan_session.end_time = datetime.now()
        scan_session.is_active = False
        
        db.commit()
        db.refresh(scan_session)
        return scan_session 