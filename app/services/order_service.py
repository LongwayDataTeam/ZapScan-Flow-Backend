from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import pandas as pd
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.order import OrderCreate, OrderUpdate, OrderSearch, OrderUploadResponse


class OrderService:
    
    @staticmethod
    def create_order(db: Session, order_data: OrderCreate) -> Order:
        """Create a new order with items"""
        # Create order
        order_dict = order_data.dict(exclude={'items'})
        db_order = Order(**order_dict)
        
        # Determine if multi-SKU or multi-quantity
        unique_g_codes = set(item.g_code for item in order_data.items)
        total_quantity = sum(item.quantity for item in order_data.items)
        
        db_order.is_multi_sku = len(unique_g_codes) > 1
        db_order.is_multi_quantity = total_quantity > len(order_data.items)
        db_order.total_items = total_quantity
        
        db.add(db_order)
        db.flush()  # Get the order ID
        
        # Create order items
        for item_data in order_data.items:
            db_item = OrderItem(
                order_id=db_order.id,
                **item_data.dict()
            )
            db.add(db_item)
        
        db.commit()
        db.refresh(db_order)
        return db_order
    
    @staticmethod
    def get_order(db: Session, order_id: int) -> Optional[Order]:
        """Get order by ID"""
        return db.query(Order).filter(Order.id == order_id).first()
    
    @staticmethod
    def get_order_by_tracker(db: Session, shipment_tracker: str) -> Optional[Order]:
        """Get order by shipment tracker"""
        return db.query(Order).filter(Order.shipment_tracker == shipment_tracker).first()
    
    @staticmethod
    def get_orders(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[OrderSearch] = None
    ) -> List[Order]:
        """Get orders with optional search filters"""
        query = db.query(Order)
        
        if search:
            filters = []
            if search.shipment_tracker:
                filters.append(Order.shipment_tracker.ilike(f"%{search.shipment_tracker}%"))
            if search.order_id:
                filters.append(Order.order_id.ilike(f"%{search.order_id}%"))
            if search.channel_id:
                filters.append(Order.channel_id.ilike(f"%{search.channel_id}%"))
            if search.channel_name:
                filters.append(Order.channel_name.ilike(f"%{search.channel_name}%"))
            if search.fulfillment_status:
                filters.append(Order.fulfillment_status == search.fulfillment_status)
            if search.buyer_city:
                filters.append(Order.buyer_city.ilike(f"%{search.buyer_city}%"))
            if search.buyer_state:
                filters.append(Order.buyer_state.ilike(f"%{search.buyer_state}%"))
            if search.is_multi_sku is not None:
                filters.append(Order.is_multi_sku == search.is_multi_sku)
            if search.is_multi_quantity is not None:
                filters.append(Order.is_multi_quantity == search.is_multi_quantity)
            if search.order_date_from:
                filters.append(Order.order_date >= search.order_date_from)
            if search.order_date_to:
                filters.append(Order.order_date <= search.order_date_to)
            
            if filters:
                query = query.filter(and_(*filters))
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def count_orders(db: Session, search: Optional[OrderSearch] = None) -> int:
        """Count total orders with optional search filters"""
        query = db.query(Order)
        
        if search:
            filters = []
            if search.shipment_tracker:
                filters.append(Order.shipment_tracker.ilike(f"%{search.shipment_tracker}%"))
            if search.order_id:
                filters.append(Order.order_id.ilike(f"%{search.order_id}%"))
            if search.channel_id:
                filters.append(Order.channel_id.ilike(f"%{search.channel_id}%"))
            if search.channel_name:
                filters.append(Order.channel_name.ilike(f"%{search.channel_name}%"))
            if search.fulfillment_status:
                filters.append(Order.fulfillment_status == search.fulfillment_status)
            if search.buyer_city:
                filters.append(Order.buyer_city.ilike(f"%{search.buyer_city}%"))
            if search.buyer_state:
                filters.append(Order.buyer_state.ilike(f"%{search.buyer_state}%"))
            if search.is_multi_sku is not None:
                filters.append(Order.is_multi_sku == search.is_multi_sku)
            if search.is_multi_quantity is not None:
                filters.append(Order.is_multi_quantity == search.is_multi_quantity)
            if search.order_date_from:
                filters.append(Order.order_date >= search.order_date_from)
            if search.order_date_to:
                filters.append(Order.order_date <= search.order_date_to)
            
            if filters:
                query = query.filter(and_(*filters))
        
        return query.count()
    
    @staticmethod
    def update_order(db: Session, order_id: int, order_data: OrderUpdate) -> Optional[Order]:
        """Update order"""
        db_order = OrderService.get_order(db, order_id)
        if not db_order:
            return None
        
        update_data = order_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_order, field, value)
        
        db.commit()
        db.refresh(db_order)
        return db_order
    
    @staticmethod
    def delete_order(db: Session, order_id: int) -> bool:
        """Delete order"""
        db_order = OrderService.get_order(db, order_id)
        if not db_order:
            return False
        
        db.delete(db_order)
        db.commit()
        return True
    
    @staticmethod
    def get_multi_sku_order(db: Session, shipment_tracker: str) -> Optional[Dict[str, Any]]:
        """Get multi-SKU order details with scan progress"""
        order = OrderService.get_order_by_tracker(db, shipment_tracker)
        if not order:
            return None
        
        # Get scan progress
        scan_progress = OrderService.get_scan_progress(db, order.id)
        
        return {
            "shipment_tracker": order.shipment_tracker,
            "total_items": order.total_items,
            "items": [item.to_dict() for item in order.items],
            "fulfillment_status": order.fulfillment_status,
            "is_completed": order.fulfillment_status == "completed",
            "scan_progress": scan_progress
        }
    
    @staticmethod
    def get_scan_progress(db: Session, order_id: int) -> Dict[str, Any]:
        """Get scan progress for an order"""
        from app.models.scan import ScanCheckpoint
        
        scans = db.query(ScanCheckpoint).filter(
            ScanCheckpoint.order_id == order_id
        ).all()
        
        progress = {
            "label_scanned": False,
            "packing_scanned": False,
            "dispatch_scanned": False,
            "total_scans": len(scans),
            "completed_checkpoints": 0
        }
        
        for scan in scans:
            if scan.checkpoint_type == "label" and scan.is_completed:
                progress["label_scanned"] = True
                progress["completed_checkpoints"] += 1
            elif scan.checkpoint_type == "packing" and scan.is_completed:
                progress["packing_scanned"] = True
                progress["completed_checkpoints"] += 1
            elif scan.checkpoint_type == "dispatch" and scan.is_completed:
                progress["dispatch_scanned"] = True
                progress["completed_checkpoints"] += 1
        
        return progress
    
    @staticmethod
    def bulk_upload_orders(db: Session, file_path: str, duplicate_handling: str = "allow") -> OrderUploadResponse:
        """Bulk upload orders from CSV/Excel file with duplicate handling
        
        Args:
            db: Database session
            file_path: Path to the CSV/Excel file
            duplicate_handling: How to handle duplicates
                - "skip": Skip orders with existing tracking ID
                - "allow": Allow duplicates (create separate entries)
                - "update": Update existing order if tracking ID exists
        """
        try:
            # Read file
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            total_processed = len(df)
            successful = 0
            failed = 0
            skipped = 0
            updated = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Validate required fields
                    if pd.isna(row.get('Shipment Tracker')):
                        errors.append(f"Row {index + 1}: Missing Shipment Tracker")
                        failed += 1
                        continue
                    
                    if pd.isna(row.get('G-Code')):
                        errors.append(f"Row {index + 1}: Missing G-Code")
                        failed += 1
                        continue
                    
                    shipment_tracker = str(row['Shipment Tracker']).strip()
                    
                    # Check if order with this tracking ID already exists
                    existing_order = OrderService.get_order_by_tracker(db, shipment_tracker)
                    
                    if existing_order:
                        if duplicate_handling == "skip":
                            errors.append(f"Row {index + 1}: Order with tracking ID '{shipment_tracker}' already exists, skipping")
                            skipped += 1
                            continue
                        elif duplicate_handling == "update":
                            # Update existing order
                            order_data = {
                                "channel_id": str(row.get('Channel ID', '')).strip() if pd.notna(row.get('Channel ID')) else None,
                                "order_id": str(row.get('Order ID/PO ID/Shipment Number', '')).strip(),
                                "po_id": str(row.get('Order ID/PO ID/Shipment Number', '')).strip(),
                                "shipment_number": str(row.get('Order ID/PO ID/Shipment Number', '')).strip(),
                                "sub_order_id": str(row.get('Sub Order ID/Invoice Number', '')).strip() if pd.notna(row.get('Sub Order ID/Invoice Number')) else None,
                                "invoice_number": str(row.get('Invoice Number', '')).strip() if pd.notna(row.get('Invoice Number')) else None,
                                "courier": str(row.get('Courier', '')).strip() if pd.notna(row.get('Courier')) else None,
                                "channel_name": str(row.get('Channel Name', '')).strip() if pd.notna(row.get('Channel Name')) else None,
                                "channel_listing_id": str(row.get('Channel Listing ID', '')).strip() if pd.notna(row.get('Channel Listing ID')) else None,
                                "total_amount": float(row.get('Amount', 0)) if pd.notna(row.get('Amount')) else None,
                                "payment_mode": str(row.get('Payment Mode', '')).strip() if pd.notna(row.get('Payment Mode')) else None,
                                "order_status": str(row.get('Order Status', '')).strip() if pd.notna(row.get('Order Status')) else None,
                                "buyer_city": str(row.get('Buyer City', '')).strip() if pd.notna(row.get('Buyer City')) else None,
                                "buyer_state": str(row.get('Buyer State', '')).strip() if pd.notna(row.get('Buyer State')) else None,
                                "buyer_pincode": str(row.get('Buyer Pincode', '')).strip() if pd.notna(row.get('Buyer Pincode')) else None,
                            }
                            
                            # Update order
                            OrderService.update_order(db, existing_order.id, OrderUpdate(**order_data))
                            updated += 1
                            continue
                        # If duplicate_handling == "allow", continue to create new order
                    
                    # Create order data
                    order_data = {
                        "channel_id": str(row.get('Channel ID', '')).strip() if pd.notna(row.get('Channel ID')) else None,
                        "order_id": str(row.get('Order ID/PO ID/Shipment Number', '')).strip(),
                        "po_id": str(row.get('Order ID/PO ID/Shipment Number', '')).strip(),
                        "shipment_number": str(row.get('Order ID/PO ID/Shipment Number', '')).strip(),
                        "sub_order_id": str(row.get('Sub Order ID/Invoice Number', '')).strip() if pd.notna(row.get('Sub Order ID/Invoice Number')) else None,
                        "invoice_number": str(row.get('Invoice Number', '')).strip() if pd.notna(row.get('Invoice Number')) else None,
                        "shipment_tracker": shipment_tracker,
                        "courier": str(row.get('Courier', '')).strip() if pd.notna(row.get('Courier')) else None,
                        "channel_name": str(row.get('Channel Name', '')).strip() if pd.notna(row.get('Channel Name')) else None,
                        "channel_listing_id": str(row.get('Channel Listing ID', '')).strip() if pd.notna(row.get('Channel Listing ID')) else None,
                        "total_amount": float(row.get('Amount', 0)) if pd.notna(row.get('Amount')) else None,
                        "payment_mode": str(row.get('Payment Mode', '')).strip() if pd.notna(row.get('Payment Mode')) else None,
                        "order_status": str(row.get('Order Status', '')).strip() if pd.notna(row.get('Order Status')) else None,
                        "buyer_city": str(row.get('Buyer City', '')).strip() if pd.notna(row.get('Buyer City')) else None,
                        "buyer_state": str(row.get('Buyer State', '')).strip() if pd.notna(row.get('Buyer State')) else None,
                        "buyer_pincode": str(row.get('Buyer Pincode', '')).strip() if pd.notna(row.get('Buyer Pincode')) else None,
                        "items": [{
                            "g_code": str(row.get('G-Code', '')).strip(),
                            "ean_code": str(row.get('EAN-Code', '')).strip() if pd.notna(row.get('EAN-Code')) else None,
                            "product_sku_code": str(row.get('Product Sku Code', '')).strip() if pd.notna(row.get('Product Sku Code')) else None,
                            "quantity": int(row.get('Qty', 1)) if pd.notna(row.get('Qty')) else 1,
                            "amount": float(row.get('Amount', 0)) if pd.notna(row.get('Amount')) else None
                        }]
                    }
                    
                    # Create order
                    order_create = OrderCreate(**order_data)
                    OrderService.create_order(db, order_create)
                    successful += 1
                    
                except Exception as e:
                    errors.append(f"Row {index + 1}: {str(e)}")
                    failed += 1
            
            # Create appropriate message based on duplicate handling
            if duplicate_handling == "skip":
                message = f"Processed {total_processed} orders. {successful} created, {skipped} skipped (duplicates), {failed} failed."
            elif duplicate_handling == "update":
                message = f"Processed {total_processed} orders. {successful} created, {updated} updated, {failed} failed."
            else:  # allow
                message = f"Processed {total_processed} orders. {successful} successful, {failed} failed."
            
            return OrderUploadResponse(
                total_processed=total_processed,
                successful=successful,
                failed=failed,
                errors=errors,
                message=message
            )
            
        except Exception as e:
            return OrderUploadResponse(
                total_processed=0,
                successful=0,
                failed=0,
                errors=[f"File processing error: {str(e)}"],
                message="Failed to process file"
            )
    
    @staticmethod
    def get_dashboard_stats(db: Session) -> Dict[str, Any]:
        """Get dashboard statistics"""
        today = datetime.now().date()
        
        # Today's orders
        today_orders = db.query(Order).filter(
            func.date(Order.created_at) == today
        ).count()
        
        # Today's dispatches
        today_dispatches = db.query(Order).filter(
            and_(
                func.date(Order.updated_at) == today,
                Order.fulfillment_status == "completed"
            )
        ).count()
        
        # Pending orders by status
        pending_labels = db.query(Order).filter(Order.fulfillment_status == "pending").count()
        label_printed = db.query(Order).filter(Order.fulfillment_status == "label_printed").count()
        packed = db.query(Order).filter(Order.fulfillment_status == "packed").count()
        
        # Multi-SKU orders
        multi_sku_orders = db.query(Order).filter(Order.is_multi_sku == True).count()
        
        return {
            "today_orders": today_orders,
            "today_dispatches": today_dispatches,
            "pending_labels": pending_labels,
            "label_printed": label_printed,
            "packed": packed,
            "multi_sku_orders": multi_sku_orders,
            "total_orders": db.query(Order).count()
        } 