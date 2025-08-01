#!/usr/bin/env python3
"""
Google Sheets Service for data synchronization
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
    
    def sync_tracker_data(self, tracker_data: Dict[str, Any]) -> bool:
        """Sync tracker data to Google Sheets"""
        if not self.initialized:
            if not self.initialize():
                return False
        
        try:
            # Open spreadsheet
            spreadsheet = self.sheets_service.open_by_key(self.spreadsheet_id)
            
            # Try to get the worksheet, create it if it doesn't exist
            try:
                worksheet = spreadsheet.worksheet(self.worksheet_name)
                logger.info(f"Found existing worksheet '{self.worksheet_name}' in Google Sheets")
            except WorksheetNotFound:
                # Create the worksheet if it doesn't exist
                try:
                    worksheet = spreadsheet.add_worksheet(title=self.worksheet_name, rows=1000, cols=21)
                    logger.info(f"Created new worksheet '{self.worksheet_name}' in Google Sheets")
                except Exception as create_error:
                    logger.error(f"Failed to create worksheet '{self.worksheet_name}': {create_error}")
                    # Try to get the worksheet again in case it was created by another process
                    try:
                        worksheet = spreadsheet.worksheet(self.worksheet_name)
                        logger.info(f"Retrieved worksheet '{self.worksheet_name}' after creation attempt")
                    except WorksheetNotFound:
                        logger.error(f"Worksheet '{self.worksheet_name}' still not found after creation attempt")
                        return False
            
            # Prepare data for Google Sheets
            row_data = [
                tracker_data.get('tracker_code', ''),
                tracker_data.get('shipment_tracker', ''),
                tracker_data.get('channel_id', ''),
                tracker_data.get('order_id', ''),
                tracker_data.get('sub_order_id', ''),
                tracker_data.get('courier', ''),
                tracker_data.get('channel_name', ''),
                tracker_data.get('g_code', ''),
                tracker_data.get('ean_code', ''),
                tracker_data.get('product_sku_code', ''),
                tracker_data.get('channel_listing_id', ''),
                tracker_data.get('qty', ''),
                tracker_data.get('amount', ''),
                tracker_data.get('payment_mode', ''),
                tracker_data.get('order_status', ''),
                tracker_data.get('buyer_city', ''),
                tracker_data.get('buyer_state', ''),
                tracker_data.get('buyer_pincode', ''),
                tracker_data.get('invoice_number', ''),
                tracker_data.get('last_updated', ''),
                datetime.now().isoformat()  # Sync timestamp
            ]
            
            # Check if tracker already exists (by tracker_code)
            existing_rows = worksheet.get_all_values()
            tracker_code = tracker_data.get('tracker_code', '')
            
            # Find existing row
            existing_row_index = None
            for i, row in enumerate(existing_rows):
                if row and row[0] == tracker_code:
                    existing_row_index = i + 1  # Google Sheets is 1-indexed
                    break
            
            if existing_row_index:
                # Update existing row
                worksheet.update(f'A{existing_row_index}:U{existing_row_index}', [row_data])
                logger.info(f"Updated tracker {tracker_code} in Google Sheets")
            else:
                # Add new row
                worksheet.append_row(row_data)
                logger.info(f"Added tracker {tracker_code} to Google Sheets")
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing to Google Sheets: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def sync_all_tracker_data(self, all_tracker_data: Dict[str, Any]) -> bool:
        """Sync all tracker data to Google Sheets - Override mode"""
        if not self.initialized:
            if not self.initialize():
                return False
        
        try:
            # Open spreadsheet
            spreadsheet = self.sheets_service.open_by_key(self.spreadsheet_id)
            
            # Try to get the worksheet, create it if it doesn't exist
            try:
                worksheet = spreadsheet.worksheet(self.worksheet_name)
                logger.info(f"Found existing worksheet '{self.worksheet_name}' in Google Sheets")
            except WorksheetNotFound:
                # Create the worksheet if it doesn't exist
                try:
                    worksheet = spreadsheet.add_worksheet(title=self.worksheet_name, rows=1000, cols=21)
                    logger.info(f"Created new worksheet '{self.worksheet_name}' in Google Sheets")
                except Exception as create_error:
                    logger.error(f"Failed to create worksheet '{self.worksheet_name}': {create_error}")
                    # Try to get the worksheet again in case it was created by another process
                    try:
                        worksheet = spreadsheet.worksheet(self.worksheet_name)
                        logger.info(f"Retrieved worksheet '{self.worksheet_name}' after creation attempt")
                    except WorksheetNotFound:
                        logger.error(f"Worksheet '{self.worksheet_name}' still not found after creation attempt")
                        return False
            
            # Clear all existing data (including headers)
            worksheet.clear()
            logger.info("Cleared existing data from Google Sheets")
            
            # Prepare headers
            headers = [
                'Tracker Code', 'Tracking ID', 'Channel ID', 'Order ID', 'Sub Order ID',
                'Stage', 'Status', 'Courier', 'Channel Name', 'G-Code', 'EAN-Code', 'Product SKU',
                'Channel Listing ID', 'Quantity', 'Amount', 'Payment Mode', 'Order Status',
                'Buyer City', 'Buyer State', 'Buyer Pincode', 'Invoice Number',
                'Last Updated', 'Sync Timestamp'
            ]
            
            # Add headers
            worksheet.update('A1:W1', [headers])
            logger.info("Added headers to Google Sheets")
            
            # Prepare all data rows
            all_rows = []
            for tracker_code, tracker_data in all_tracker_data.items():
                # Calculate Stage and Status based on tracker status
                status = tracker_data.get('status', {})
                
                # Determine Stage
                if status.get('cancelled', False):
                    stage = 'Dispatch Cancelled'
                elif status.get('dispatch', False):
                    stage = 'Dispatch'
                elif status.get('packing', False):
                    stage = 'Packing'
                elif status.get('label', False):
                    stage = 'Label'
                else:
                    stage = 'Label'
                
                # Determine Status
                if status.get('cancelled', False):
                    current_status = 'Cancelled'
                elif status.get('dispatch', False):
                    current_status = 'Dispatched'
                elif status.get('pending', False) and status.get('packing', False):
                    current_status = 'Dispatch Pending'
                elif status.get('pending', False) and status.get('label', False) and not status.get('packing', False):
                    current_status = 'Packing Hold'
                elif status.get('packing', False):
                    current_status = 'Packing Scanned'
                elif status.get('label', False):
                    current_status = 'Packing Pending Shipment'
                else:
                    current_status = 'Label yet to Scan'
                
                row_data = [
                    str(tracker_data.get('tracker_code', '')),
                    str(tracker_data.get('shipment_tracker', '')),
                    str(tracker_data.get('channel_id', '')),
                    str(tracker_data.get('order_id', '')),
                    str(tracker_data.get('sub_order_id', '')),
                    stage,
                    current_status,
                    str(tracker_data.get('courier', '')),
                    str(tracker_data.get('channel_name', '')),
                    str(tracker_data.get('g_code', '')),
                    str(tracker_data.get('ean_code', '')),
                    str(tracker_data.get('product_sku_code', '')),
                    str(tracker_data.get('channel_listing_id', '')),
                    str(tracker_data.get('qty', '')),
                    str(tracker_data.get('amount', '')),
                    str(tracker_data.get('payment_mode', '')),
                    str(tracker_data.get('order_status', '')),
                    str(tracker_data.get('buyer_city', '')),
                    str(tracker_data.get('buyer_state', '')),
                    str(tracker_data.get('buyer_pincode', '')),
                    str(tracker_data.get('invoice_number', '')),
                    str(tracker_data.get('last_updated', '')),
                    datetime.now().isoformat()  # Sync timestamp
                ]
                all_rows.append(row_data)
            
            # Add all data rows in batch
            if all_rows:
                worksheet.append_rows(all_rows)
                logger.info(f"Added {len(all_rows)} data rows to Google Sheets")
            
            # Set column widths for better formatting (no text wrapping)
            try:
                # Set reasonable column widths for better readability (23 columns now)
                column_widths = [200, 200, 150, 150, 150, 150, 150, 150, 150, 150, 200, 200, 100, 100, 150, 150, 150, 150, 100, 150, 200, 200]
                for i, width in enumerate(column_widths, 1):
                    worksheet.set_column_width(i, width)
                logger.info("Set column widths for better formatting")
            except Exception as format_error:
                logger.warning(f"Could not set column widths: {format_error}")
            
            # Set text wrapping to false for all cells
            try:
                worksheet.format('A1:W' + str(len(all_rows) + 1), {
                    "wrapStrategy": "CLIP"
                })
                logger.info("Disabled text wrapping for all cells")
            except Exception as wrap_error:
                logger.warning(f"Could not disable text wrapping: {wrap_error}")
            
            logger.info(f"Successfully synced {len(all_tracker_data)} trackers to Google Sheets (override mode)")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing all data to Google Sheets: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

# Create singleton instance
gsheets_service = GoogleSheetsService() 