#!/usr/bin/env python3
"""
Google Sheets Service for data synchronization - EXACT SAME LOGIC AS simple_paste.py
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any
import gspread
from gspread import WorksheetNotFound
from google.oauth2.service_account import Credentials
from google.auth.exceptions import GoogleAuthError
import logging

# Import firestore service
from app.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self.sheets_service = None
        self.spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '1rLSCtZkVU3WJ8qQz1l5Tv3L6aaAuqf_iKGaKaLMh2zQ')
        self.credentials_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', 'gsheet-onescan-service.json')
        self.worksheet_name = os.getenv('GOOGLE_SHEETS_WORKSHEET_NAME', 'tracker')
        self.initialized = False
        
    def initialize(self):
        """Initialize Google Sheets service"""
        try:
            if not self.spreadsheet_id:
                logger.warning("Google Sheets not configured - spreadsheet ID not set")
                return False
                
            if not os.path.exists(self.credentials_path):
                logger.warning(f"Google Sheets credentials not found at {self.credentials_path}")
                return False
            
            # Set up credentials
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=scope
            )
            
            self.sheets_service = gspread.authorize(credentials)
            
            # Test access to the spreadsheet
            try:
                spreadsheet = self.sheets_service.open_by_key(self.spreadsheet_id)
                logger.info(f"Successfully accessed spreadsheet: {spreadsheet.title}")
            except Exception as e:
                logger.error(f"Cannot access spreadsheet {self.spreadsheet_id}: {e}")
                return False
            
            self.initialized = True
            logger.info("Google Sheets service initialized successfully")
            return True
            
        except GoogleAuthError as e:
            logger.error(f"Google Sheets authentication error: {e}")
            return False
        except Exception as e:
            logger.error(f"Google Sheets initialization error: {e}")
            return False

    def get_stage_and_status_from_flags(self, status):
        """Calculate stage and status from boolean flags using exact frontend logic"""
        # Get scan status information
        label_scanned = status.get('label', False)
        packing_scanned = status.get('packing', False)
        dispatch_scanned = status.get('dispatch', False)
        cancelled = status.get('cancelled', False)
        pending = status.get('pending', False)
        
        # Determine Stage (EXACTLY matching frontend getCurrentStage logic)
        if cancelled:
            stage = 'Dispatch Cancelled'
        elif dispatch_scanned:
            stage = 'Dispatch'
        # Dispatch Pending: label = true, packing = true, pending = true
        elif label_scanned and packing_scanned and pending:
            stage = 'Dispatch Pending'
        elif packing_scanned:
            stage = 'Packing'
        # Packing Hold: label = true, pending = true (but packing = false)
        elif label_scanned and pending:
            stage = 'Packing Hold'
        elif label_scanned:
            stage = 'Packing Pending'
        else:
            stage = 'Label'
        
        # Determine Status (EXACTLY matching frontend getCurrentStatusWithPackingPending logic)
        if cancelled:
            current_status = 'Cancelled'
        elif dispatch_scanned:
            current_status = 'Dispatched'
        # Dispatch Pending: label = true, packing = true, pending = true
        elif label_scanned and packing_scanned and pending:
            current_status = 'Dispatch Pending'
        elif packing_scanned:
            current_status = 'Packing Scanned'
        # Packing Hold: label = true, pending = true (but packing = false)
        elif label_scanned and pending:
            current_status = 'Packing Hold'
        elif label_scanned:
            current_status = 'Packing Pending Shipment'
        else:
            current_status = 'Label yet to Scan'
        
        return stage, current_status

    def get_frontend_data(self):
        """Get the exact data that the frontend shows - no modifications"""
        logger.info("📊 Getting frontend data...")
        
        try:
            # Get the exact same data that the frontend uses
            all_status = firestore_service.get_all_tracker_status()
            all_data = firestore_service.get_all_tracker_data()
            
            trackers = []
            # Use the same logic as the backend API
            for doc_id, tracker_data in all_data.items():
                if doc_id in all_status:
                    status = all_status[doc_id]
                    next_scan = "label" if not status.get("label", False) else \
                               "packing" if not status.get("packing", False) else \
                               "dispatch" if not status.get("dispatch", False) else "completed"
                    
                    # Get the original tracking ID from tracker data
                    original_tracking_id = tracker_data.get('shipment_tracker', doc_id)
                    
                    trackers.append({
                        "tracker_code": doc_id,
                        "original_tracking_id": original_tracking_id,
                        "status": status,
                        "next_available_scan": next_scan,
                        "details": tracker_data
                    })
                else:
                    # Get the original tracking ID from tracker data
                    original_tracking_id = tracker_data.get('shipment_tracker', doc_id)
                    
                    trackers.append({
                        "tracker_code": doc_id,
                        "original_tracking_id": original_tracking_id,
                        "status": {"label": False, "packing": False, "dispatch": False, "pending": False},
                        "next_available_scan": "label",
                        "details": tracker_data
                    })
            
            logger.info(f"📊 Found {len(trackers)} trackers (exact frontend data)")
            return trackers
            
        except Exception as e:
            logger.error(f"❌ Error getting frontend data: {e}")
            return []

    def simple_paste_to_sheets(self):
        """Simple paste - no modifications, just paste what frontend shows"""
        logger.info("🔄 Simple Paste to Google Sheets (No Modifications)")
        
        try:
            # Initialize services
            logger.info("🔧 Initializing services...")
            self.initialize()
            
            # Get frontend data
            trackers = self.get_frontend_data()
            
            if not trackers:
                logger.error("❌ No tracker data found")
                return False
            
            logger.info(f"📊 Found {len(trackers)} trackers to paste")
            
            # Open spreadsheet and worksheet
            spreadsheet = self.sheets_service.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(self.worksheet_name)
            
            logger.info(f"📊 Opened spreadsheet: {spreadsheet.title}")
            logger.info(f"📋 Using worksheet: {self.worksheet_name}")
            
            # Clear all existing data
            logger.info("🧹 Clearing existing data...")
            worksheet.clear()
            
            # Prepare headers
            headers = [
                'Tracker Code', 'Tracking ID', 'Order ID', 'Stage', 'Status',
                'Channel', 'Courier', 'City', 'State', 'Pincode', 'Amount', 'Qty', 'Payment', 'Order Status',
                'G-Code', 'EAN-Code', 'Product SKU', 'Listing ID', 'Invoice', 'Sub Order ID', 'Last Updated'
            ]
            
            # Add headers first
            logger.info("📋 Adding headers...")
            worksheet.update('A1:U1', [headers])
            
            # Prepare all data rows - NO MODIFICATIONS
            logger.info("📝 Preparing data rows (no modifications)...")
            all_rows = []
            
            for tracker in trackers:
                # Get details from the tracker
                details = tracker['details']
                status = tracker['status']
                
                # Calculate stage and status from boolean flags (exact frontend logic)
                stage, current_status = self.get_stage_and_status_from_flags(status)
                
                # Format amount with ₹ symbol
                amount = details.get('amount', 0)
                formatted_amount = f"₹{amount}" if amount else "₹0"
                
                # Format last updated timestamp
                last_updated = details.get('last_updated', '')
                formatted_last_updated = "-" if not last_updated else last_updated
                
                # Use the calculated stage and status
                row_data = [
                    str(tracker['tracker_code']),  # Tracker Code
                    str(tracker['original_tracking_id']),  # Tracking ID
                    str(details.get('order_id', '')),  # Order ID
                    stage,  # Stage (calculated from flags)
                    current_status,  # Status (calculated from flags)
                    str(details.get('channel_name', '')),  # Channel
                    str(details.get('courier', '')),  # Courier
                    str(details.get('buyer_city', '')),  # City
                    str(details.get('buyer_state', '')),  # State
                    str(details.get('buyer_pincode', '')),  # Pincode
                    formatted_amount,  # Amount (with ₹ symbol)
                    str(details.get('qty', '')),  # Qty
                    str(details.get('payment_mode', '')),  # Payment
                    str(details.get('order_status', '')),  # Order Status
                    str(details.get('g_code', '')),  # G-Code
                    str(details.get('ean_code', '')),  # EAN-Code
                    str(details.get('product_sku_code', '')),  # Product SKU
                    str(details.get('channel_listing_id', '')),  # Listing ID
                    str(details.get('invoice_number', '')),  # Invoice
                    str(details.get('sub_order_id', '')),  # Sub Order ID
                    formatted_last_updated  # Last Updated
                ]
                all_rows.append(row_data)
            
            # Paste all data at once
            if all_rows:
                logger.info(f"📋 Pasting {len(all_rows)} data rows...")
                
                # Calculate the range for all data
                end_row = len(all_rows) + 1  # +1 for headers
                paste_range = f"A2:U{end_row}"
                
                # Paste all data at once
                worksheet.update(paste_range, all_rows)
                
                logger.info(f"✅ Successfully pasted {len(all_rows)} rows")
                logger.info(f"📊 Data range: A2:U{end_row}")
                
                # Verify the paste
                all_values = worksheet.get_all_values()
                logger.info(f"✅ Verified: {len(all_values)} total rows in sheet")
                logger.info(f"📋 Headers: {len(all_values[0]) if all_values else 0} columns")
                logger.info(f"📊 Data: {len(all_values) - 1 if len(all_values) > 1 else 0} rows")
                
                # Show sample data
                if len(all_values) > 1:
                    logger.info("📋 Sample data (first row):")
                    first_row = all_values[1]
                    for i, value in enumerate(first_row[:5], 1):
                        logger.info(f"   Column {i}: {value}")
                
                # Disable text wrapping
                try:
                    worksheet.format(f'A1:U{end_row}', {
                        "wrapStrategy": "CLIP"
                    })
                    logger.info("📄 Disabled text wrapping")
                except Exception as wrap_error:
                    logger.warning(f"⚠️ Could not disable text wrapping: {wrap_error}")
                
                logger.info(f"🎉 Simple paste completed successfully!")
                logger.info(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"📊 Spreadsheet URL: https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}")
                
                return True
            else:
                logger.error("❌ No data rows to paste")
                return False
                
        except Exception as e:
            logger.error(f"❌ Simple paste error: {e}")
            import traceback
            logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
            return False

    def sync_all_tracker_data(self, all_tracker_data: Dict[str, Any]) -> bool:
        """Sync all tracker data to Google Sheets - EXACT SAME AS simple_paste.py"""
        # This method now just calls the simple_paste_to_sheets method
        return self.simple_paste_to_sheets()

# Create singleton instance
gsheets_service = GoogleSheetsService() 