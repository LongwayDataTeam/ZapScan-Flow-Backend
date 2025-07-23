import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsService:
    """Service for direct Google Sheets operations without database"""
    
    def __init__(self):
        self.scope = ['https://www.googleapis.com/auth/spreadsheets']
        self.credentials = None
        self.sheets_service = None
        self.spreadsheet_id = "1t128cQFD3dtJKh2lVdERytsM9ZO7npwV23c3vQMwsgA"  # User's specific spreadsheet
        self.processor_tab = "Scan Processor"  # Tab for workflow processing
        self.database_tab = "Database"  # Tab for storing data
        self._setup_google_sheets()
    
    def _setup_google_sheets(self):
        """Setup Google Sheets API credentials"""
        try:
            # Try to load credentials from service_key.json file first
            service_key_path = os.path.join(os.getcwd(), "service_key.json")
            if os.path.exists(service_key_path):
                print(f"📁 Found service_key.json at: {service_key_path}")
                self.credentials = Credentials.from_service_account_file(
                    service_key_path, scopes=self.scope
                )
                print("✅ Loaded credentials from service_key.json")
            else:
                # Fallback to environment variable
                creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
                if creds_json:
                    creds_dict = json.loads(creds_json)
                    self.credentials = Credentials.from_service_account_info(
                        creds_dict, scopes=self.scope
                    )
                    print("✅ Loaded credentials from environment variable")
                else:
                    print("❌ No credentials found in service_key.json or environment variable")
                    return
            
            # Use user's spreadsheet ID
            if self.credentials:
                self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
                print(f"✅ Google Sheets API configured successfully")
                print(f"📊 Spreadsheet ID: {self.spreadsheet_id}")
                print(f"⚙️ Processor Tab: {self.processor_tab}")
                print(f"💾 Database Tab: {self.database_tab}")
                
                # Test the connection
                try:
                    # Try to get spreadsheet info to verify connection
                    spreadsheet = self.sheets_service.spreadsheets().get(
                        spreadsheetId=self.spreadsheet_id
                    ).execute()
                    print(f"✅ Successfully connected to spreadsheet: {spreadsheet.get('properties', {}).get('title', 'Unknown')}")
                except Exception as e:
                    print(f"❌ Failed to connect to spreadsheet: {e}")
                    print("Please check:")
                    print("1. Service account has access to the spreadsheet")
                    print("2. Spreadsheet ID is correct")
                    print("3. Service account email is shared with the spreadsheet")
                    
            else:
                print("⚠️ Google Sheets credentials not found")
                
        except Exception as e:
            print(f"❌ Google Sheets setup failed: {e}")
    
    def get_next_empty_row(self, sheet_name: str) -> int:
        """Get the next empty row in a sheet"""
        try:
            range_name = f"{sheet_name}!A:A"
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            return len(values) + 1
            
        except Exception as e:
            print(f"❌ Error getting next empty row: {e}")
            return 1
    
    def append_data_to_sheet(self, data: List[List], sheet_name: str) -> bool:
        """Append data to the next empty row in a sheet"""
        try:
            if not self.sheets_service:
                print("❌ Google Sheets not configured")
                return False
            
            # Get next empty row
            next_row = self.get_next_empty_row(sheet_name)
            
            # Append data
            range_name = f"{sheet_name}!A{next_row}"
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": data}
            ).execute()
            
            print(f"✅ Data appended to {sheet_name} at row {next_row}")
            return True
            
        except Exception as e:
            print(f"❌ Error appending data: {e}")
            return False
    
    def upload_orders_to_sheets(self, orders_data: List[Dict]) -> Dict[str, Any]:
        """Upload orders data to Scan Processor tab"""
        try:
            if not orders_data:
                return {"success": False, "error": "No data to upload"}
            
            # Prepare headers
            headers = [
                "ID", "Shipment Tracker", "Order ID", "Channel Name", 
                "Buyer City", "Buyer State", "Total Amount", "Fulfillment Status",
                "Is Multi SKU", "Is Multi Quantity", "Total Items", "Created At"
            ]
            
            # Prepare data rows
            rows = [headers]
            for order in orders_data:
                rows.append([
                    order.get('id', ''),
                    order.get('shipment_tracker', ''),
                    order.get('order_id', ''),
                    order.get('channel_name', ''),
                    order.get('buyer_city', ''),
                    order.get('buyer_state', ''),
                    order.get('total_amount', ''),
                    order.get('fulfillment_status', ''),
                    order.get('is_multi_sku', ''),
                    order.get('is_multi_quantity', ''),
                    order.get('total_items', ''),
                    order.get('created_at', '')
                ])
            
            # Upload to Scan Processor tab
            success = self.append_data_to_sheet(rows, self.processor_tab)
            
            return {
                "success": success,
                "records_uploaded": len(orders_data),
                "sheet_name": self.processor_tab,
                "message": f"Uploaded {len(orders_data)} orders to {self.processor_tab}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def upload_scans_to_sheets(self, scans_data: List[Dict]) -> Dict[str, Any]:
        """Upload scan data to Scan Processor tab"""
        try:
            if not scans_data:
                return {"success": False, "error": "No scan data to upload"}
            
            # Prepare headers
            headers = [
                "ID", "Order ID", "Checkpoint Type", "Scan Time", 
                "Scanned By", "Status", "Is Completed", "Created At"
            ]
            
            # Prepare data rows
            rows = [headers]
            for scan in scans_data:
                rows.append([
                    scan.get('id', ''),
                    scan.get('order_id', ''),
                    scan.get('checkpoint_type', ''),
                    scan.get('scan_time', ''),
                    scan.get('scanned_by', ''),
                    scan.get('status', ''),
                    scan.get('is_completed', ''),
                    scan.get('created_at', '')
                ])
            
            # Upload to Scan Processor tab
            success = self.append_data_to_sheet(rows, self.processor_tab)
            
            return {
                "success": success,
                "records_uploaded": len(scans_data),
                "sheet_name": self.processor_tab,
                "message": f"Uploaded {len(scans_data)} scans to {self.processor_tab}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_workflow_data(self, orders_data: List[Dict]) -> Dict[str, Any]:
        """Process workflow data and update Scan Processor tab"""
        try:
            # Simulate scan processing
            processed_scans = []
            for order in orders_data:
                # Create scan checkpoints for each order
                scan_types = ["label", "packing", "dispatch"]
                for scan_type in scan_types:
                    processed_scans.append({
                        "id": len(processed_scans) + 1,
                        "order_id": order.get('id'),
                        "checkpoint_type": scan_type,
                        "scan_time": datetime.now().isoformat(),
                        "scanned_by": "system",
                        "status": "success",
                        "is_completed": True,
                        "created_at": datetime.now().isoformat()
                    })
            
            # Upload processed data to Scan Processor tab
            orders_result = self.upload_orders_to_sheets(orders_data)
            scans_result = self.upload_scans_to_sheets(processed_scans)
            
            return {
                "success": orders_result["success"] and scans_result["success"],
                "orders_processed": len(orders_data),
                "scans_processed": len(processed_scans),
                "orders_result": orders_result,
                "scans_result": scans_result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def clear_and_move_to_database(self) -> Dict[str, Any]:
        """Move data from Scan Processor to Database tab"""
        try:
            # Get current data from Scan Processor tab
            current_data = self.get_sheet_data(self.processor_tab)
            
            if len(current_data) <= 1:  # Only header or empty
                return {
                    "success": True,
                    "message": "No data to move",
                    "moved_orders": 0,
                    "moved_scans": 0
                }
            
            # Move data to Database tab
            data_moved = self.move_data_to_tab(self.processor_tab, self.database_tab)
            
            # Clear Scan Processor tab
            self.clear_sheet(self.processor_tab)
            
            return {
                "success": True,
                "message": f"Data moved from {self.processor_tab} to {self.database_tab}",
                "moved_records": data_moved,
                "moved_orders": data_moved,
                "moved_scans": data_moved,
                "source_tab": self.processor_tab,
                "destination_tab": self.database_tab
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_sheet_data(self, sheet_name: str) -> List[List]:
        """Get all data from a sheet"""
        try:
            range_name = f"{sheet_name}!A:Z"
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            return result.get('values', [])
            
        except Exception as e:
            print(f"❌ Error getting sheet data: {e}")
            return []
    
    def create_new_tab(self, tab_name: str) -> bool:
        """Create a new tab in the spreadsheet"""
        try:
            request = {
                "addSheet": {
                    "properties": {
                        "title": tab_name
                    }
                }
            }
            
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": [request]}
            ).execute()
            
            print(f"✅ Created new tab: {tab_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating tab: {e}")
            return False
    
    def move_data_to_tab(self, source_sheet: str, target_sheet: str) -> int:
        """Move data from source sheet to target sheet"""
        try:
            data = self.get_sheet_data(source_sheet)
            if not data:
                return 0
            
            # Append data to target sheet
            success = self.append_data_to_sheet(data, target_sheet)
            return len(data) if success else 0
            
        except Exception as e:
            print(f"❌ Error moving data: {e}")
            return 0
    
    def clear_sheet(self, sheet_name: str) -> bool:
        """Clear all data from a sheet"""
        try:
            range_name = f"{sheet_name}!A:Z"
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            print(f"✅ Cleared sheet: {sheet_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error clearing sheet: {e}")
            return False
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status from Scan Processor tab"""
        try:
            data = self.get_sheet_data(self.processor_tab)
            
            # Count records (excluding header)
            total_records = max(0, len(data) - 1)
            
            # Calculate scan progress
            scan_progress = {"label": 0, "packing": 0, "dispatch": 0}
            if len(data) > 1:
                for row in data[1:]:  # Skip header
                    if len(row) >= 3:
                        scan_type = row[2].lower()
                        if scan_type in scan_progress:
                            scan_progress[scan_type] += 1
            
            # Calculate percentages
            scan_percentages = {}
            for scan_type, count in scan_progress.items():
                percentage = (count / total_records * 100) if total_records > 0 else 0
                scan_percentages[scan_type] = {
                    "count": count,
                    "percentage": round(percentage, 2)
                }
            
            return {
                "total_orders": total_records,
                "total_scans": total_records,
                "scan_progress": scan_percentages,
                "data_size_mb": (total_records * 12) / 1024,
                "can_clear": total_records > 0
            }
            
        except Exception as e:
            return {
                "total_orders": 0,
                "total_scans": 0,
                "scan_progress": {},
                "data_size_mb": 0,
                "can_clear": False,
                "error": str(e)
            } 