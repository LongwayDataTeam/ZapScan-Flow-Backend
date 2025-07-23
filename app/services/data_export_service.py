import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from app.models.order import Order, OrderItem
from app.models.scan import ScanCheckpoint, ScanSession
from app.core.config import settings


class DataExportService:
    """Service for exporting daily scan data to Google Sheets and cleaning database"""
    
    def __init__(self):
        self.scope = ['https://www.googleapis.com/auth/spreadsheets']
        self.credentials = None
        self.sheets_service = None
        self._setup_google_sheets()
    
    def _setup_google_sheets(self):
        """Setup Google Sheets API credentials"""
        try:
            # Load credentials from environment or service account file
            creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
            if creds_path and os.path.exists(creds_path):
                self.credentials = Credentials.from_service_account_file(
                    creds_path, scopes=self.scope
                )
            else:
                # Use environment variables for credentials
                creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
                if creds_json:
                    creds_dict = json.loads(creds_json)
                    self.credentials = Credentials.from_service_account_info(
                        creds_dict, scopes=self.scope
                    )
            
            if self.credentials:
                self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
                print("✅ Google Sheets API configured successfully")
            else:
                print("⚠️ Google Sheets credentials not found")
                
        except Exception as e:
            print(f"❌ Google Sheets setup failed: {e}")
    
    def export_daily_data_to_sheets(self, db: Session, date: datetime = None) -> Dict[str, Any]:
        """Export daily scan data to Google Sheets"""
        if not date:
            date = datetime.now().date()
        
        print(f"📊 Exporting data for {date} to Google Sheets...")
        
        try:
            # Get daily data
            daily_data = self._get_daily_data(db, date)
            
            # Export to Google Sheets
            if self.sheets_service:
                result = self._upload_to_sheets(daily_data, date)
                print(f"✅ Data exported to Google Sheets: {result}")
            else:
                # Fallback to CSV export
                result = self._export_to_csv(daily_data, date)
                print(f"✅ Data exported to CSV: {result}")
            
            return {
                "success": True,
                "date": date.strftime("%Y-%m-%d"),
                "records_exported": len(daily_data['orders']),
                "file_path": result
            }
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_daily_data(self, db: Session, date: datetime) -> Dict[str, Any]:
        """Get all data for a specific date"""
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # Get orders created on this date
        orders = db.query(Order).filter(
            and_(
                Order.created_at >= start_date,
                Order.created_at < end_date
            )
        ).all()
        
        # Get scan checkpoints for these orders
        order_ids = [order.id for order in orders]
        scan_checkpoints = []
        if order_ids:
            scan_checkpoints = db.query(ScanCheckpoint).filter(
                ScanCheckpoint.order_id.in_(order_ids)
            ).all()
        
        # Get scan sessions for this date
        scan_sessions = db.query(ScanSession).filter(
            and_(
                ScanSession.created_at >= start_date,
                ScanSession.created_at < end_date
            )
        ).all()
        
        return {
            "orders": [order.to_dict() for order in orders],
            "scan_checkpoints": [scan.to_dict() for scan in scan_checkpoints],
            "scan_sessions": [session.to_dict() for session in scan_sessions],
            "export_date": datetime.now().isoformat()
        }
    
    def _upload_to_sheets(self, data: Dict[str, Any], date: datetime) -> str:
        """Upload data to Google Sheets"""
        spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
        if not spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID not configured")
        
        # Prepare data for sheets
        orders_data = self._prepare_orders_for_sheets(data['orders'])
        scans_data = self._prepare_scans_for_sheets(data['scan_checkpoints'])
        
        # Upload to different sheets
        self._update_sheet(spreadsheet_id, "Orders", orders_data)
        self._update_sheet(spreadsheet_id, "Scans", scans_data)
        
        return f"Spreadsheet: {spreadsheet_id}"
    
    def _prepare_orders_for_sheets(self, orders: List[Dict]) -> List[List]:
        """Prepare orders data for Google Sheets"""
        headers = [
            "ID", "Shipment Tracker", "Order ID", "Channel Name", 
            "Buyer City", "Buyer State", "Total Amount", "Fulfillment Status",
            "Is Multi SKU", "Is Multi Quantity", "Total Items", "Created At"
        ]
        
        rows = [headers]
        for order in orders:
            rows.append([
                order['id'],
                order['shipment_tracker'],
                order['order_id'],
                order['channel_name'],
                order['buyer_city'],
                order['buyer_state'],
                order['total_amount'],
                order['fulfillment_status'],
                order['is_multi_sku'],
                order['is_multi_quantity'],
                order['total_items'],
                order['created_at']
            ])
        
        return rows
    
    def _prepare_scans_for_sheets(self, scans: List[Dict]) -> List[List]:
        """Prepare scan data for Google Sheets"""
        headers = [
            "ID", "Order ID", "Checkpoint Type", "Scan Time", 
            "Scanned By", "Status", "Is Completed", "Created At"
        ]
        
        rows = [headers]
        for scan in scans:
            rows.append([
                scan['id'],
                scan['order_id'],
                scan['checkpoint_type'],
                scan['scan_time'],
                scan['scanned_by'],
                scan['status'],
                scan['is_completed'],
                scan['created_at']
            ])
        
        return rows
    
    def _update_sheet(self, spreadsheet_id: str, sheet_name: str, data: List[List]):
        """Update a specific sheet with data"""
        try:
            # Clear existing data
            range_name = f"{sheet_name}!A:Z"
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            # Upload new data
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": data}
            ).execute()
            
        except Exception as e:
            print(f"❌ Sheet update failed for {sheet_name}: {e}")
    
    def _export_to_csv(self, data: Dict[str, Any], date: datetime) -> str:
        """Export data to CSV as fallback"""
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)
        
        date_str = date.strftime("%Y-%m-%d")
        
        # Export orders
        orders_df = pd.DataFrame(data['orders'])
        orders_file = f"{export_dir}/orders_{date_str}.csv"
        orders_df.to_csv(orders_file, index=False)
        
        # Export scans
        scans_df = pd.DataFrame(data['scan_checkpoints'])
        scans_file = f"{export_dir}/scans_{date_str}.csv"
        scans_df.to_csv(scans_file, index=False)
        
        return f"CSV files: {orders_file}, {scans_file}"
    
    def cleanup_daily_data(self, db: Session, date: datetime = None) -> Dict[str, Any]:
        """Delete daily data from database after export"""
        if not date:
            date = datetime.now().date()
        
        print(f"🧹 Cleaning up data for {date}...")
        
        try:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            
            # Get orders to delete
            orders_to_delete = db.query(Order).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at < end_date
                )
            ).all()
            
            order_ids = [order.id for order in orders_to_delete]
            
            # Delete related data first (foreign key constraints)
            if order_ids:
                # Delete scan checkpoints
                db.query(ScanCheckpoint).filter(
                    ScanCheckpoint.order_id.in_(order_ids)
                ).delete(synchronize_session=False)
                
                # Delete order items
                db.query(OrderItem).filter(
                    OrderItem.order_id.in_(order_ids)
                ).delete(synchronize_session=False)
            
            # Delete orders
            deleted_orders = db.query(Order).filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at < end_date
                )
            ).delete(synchronize_session=False)
            
            # Delete scan sessions
            deleted_sessions = db.query(ScanSession).filter(
                and_(
                    ScanSession.created_at >= start_date,
                    ScanSession.created_at < end_date
                )
            ).delete(synchronize_session=False)
            
            db.commit()
            
            return {
                "success": True,
                "date": date.strftime("%Y-%m-%d"),
                "deleted_orders": deleted_orders,
                "deleted_sessions": deleted_sessions
            }
            
        except Exception as e:
            db.rollback()
            print(f"❌ Cleanup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_daily_summary(self, db: Session, date: datetime = None) -> Dict[str, Any]:
        """Get summary statistics for daily data"""
        if not date:
            date = datetime.now().date()
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # Count orders
        total_orders = db.query(Order).filter(
            and_(
                Order.created_at >= start_date,
                Order.created_at < end_date
            )
        ).count()
        
        # Count scans
        total_scans = db.query(ScanCheckpoint).join(Order).filter(
            and_(
                Order.created_at >= start_date,
                Order.created_at < end_date
            )
        ).count()
        
        # Count by scan type
        scan_types = db.query(
            ScanCheckpoint.checkpoint_type,
            func.count(ScanCheckpoint.id)
        ).join(Order).filter(
            and_(
                Order.created_at >= start_date,
                Order.created_at < end_date
            )
        ).group_by(ScanCheckpoint.checkpoint_type).all()
        
        return {
            "date": date.strftime("%Y-%m-%d"),
            "total_orders": total_orders,
            "total_scans": total_scans,
            "scan_breakdown": dict(scan_types),
            "data_size_mb": (total_orders * 12 + total_scans * 2) / 1024  # Rough estimate
        } 