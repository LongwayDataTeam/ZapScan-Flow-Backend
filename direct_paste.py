#!/usr/bin/env python3
"""
Direct paste script for Google Sheets with proper column separation
"""

import os
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.firestore_service import firestore_service
from app.services.gsheets_service import gsheets_service

def get_stage_and_status(tracker_data):
    """Get stage and status EXACTLY matching frontend logic"""
    status = tracker_data.get('status', {})
    
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

def direct_paste_to_sheets():
    """Directly paste data to Google Sheets with proper formatting"""
    print("🔄 Direct Paste to Google Sheets")
    print("=" * 50)
    
    try:
        # Initialize services
        print("🔧 Initializing services...")
        gsheets_service.initialize()
        all_tracker_data = firestore_service.get_all_tracker_data()
        
        if not all_tracker_data:
            print("❌ No tracker data found in Firestore")
            return False
        
        print(f"📊 Found {len(all_tracker_data)} trackers to paste")
        
        # Open spreadsheet and worksheet
        spreadsheet = gsheets_service.sheets_service.open_by_key(gsheets_service.spreadsheet_id)
        worksheet = spreadsheet.worksheet(gsheets_service.worksheet_name)
        
        print(f"📊 Opened spreadsheet: {spreadsheet.title}")
        print(f"📋 Using worksheet: {gsheets_service.worksheet_name}")
        
        # Clear all existing data
        print("🧹 Clearing existing data...")
        worksheet.clear()
        
        # Prepare headers
        headers = [
            'Tracker Code', 'Tracking ID', 'Order ID', 'Stage', 'Status',
            'Channel', 'Courier', 'City', 'State', 'Pincode', 'Amount', 'Qty', 'Payment', 'Order Status',
            'G-Code', 'EAN-Code', 'Product SKU', 'Listing ID', 'Invoice', 'Sub Order ID', 'Last Updated'
        ]
        
        # Add headers first
        print("📋 Adding headers...")
        worksheet.update('A1:U1', [headers])
        
        # Prepare all data rows
        print("📝 Preparing data rows...")
        all_rows = []
        
        for tracker_code, tracker_data in all_tracker_data.items():
            # Calculate Stage and Status
            stage, current_status = get_stage_and_status(tracker_data)
            
            # Format amount with ₹ symbol
            amount = tracker_data.get('amount', 0)
            formatted_amount = f"₹{amount}" if amount else "₹0"
            
            # Format last updated timestamp
            last_updated = tracker_data.get('last_updated', '')
            formatted_last_updated = "-" if not last_updated else last_updated
            
            row_data = [
                str(tracker_code),  # Tracker Code
                str(tracker_data.get('shipment_tracker', '')),  # Tracking ID
                str(tracker_data.get('order_id', '')),  # Order ID
                stage,  # Stage
                current_status,  # Status
                str(tracker_data.get('channel_name', '')),  # Channel
                str(tracker_data.get('courier', '')),  # Courier
                str(tracker_data.get('buyer_city', '')),  # City
                str(tracker_data.get('buyer_state', '')),  # State
                str(tracker_data.get('buyer_pincode', '')),  # Pincode
                formatted_amount,  # Amount (with ₹ symbol)
                str(tracker_data.get('qty', '')),  # Qty
                str(tracker_data.get('payment_mode', '')),  # Payment
                str(tracker_data.get('order_status', '')),  # Order Status
                str(tracker_data.get('g_code', '')),  # G-Code
                str(tracker_data.get('ean_code', '')),  # EAN-Code
                str(tracker_data.get('product_sku_code', '')),  # Product SKU
                str(tracker_data.get('channel_listing_id', '')),  # Listing ID
                str(tracker_data.get('invoice_number', '')),  # Invoice
                str(tracker_data.get('sub_order_id', '')),  # Sub Order ID
                formatted_last_updated  # Last Updated
            ]
            all_rows.append(row_data)
        
        # Paste all data at once
        if all_rows:
            print(f"📋 Pasting {len(all_rows)} data rows...")
            
            # Calculate the range for all data
            end_row = len(all_rows) + 1  # +1 for headers
            paste_range = f"A2:U{end_row}"
            
            # Paste all data at once
            worksheet.update(paste_range, all_rows)
            
            print(f"✅ Successfully pasted {len(all_rows)} rows")
            print(f"📊 Data range: A2:U{end_row}")
            
            # Verify the paste
            all_values = worksheet.get_all_values()
            print(f"✅ Verified: {len(all_values)} total rows in sheet")
            print(f"📋 Headers: {len(all_values[0]) if all_values else 0} columns")
            print(f"📊 Data: {len(all_values) - 1 if len(all_values) > 1 else 0} rows")
            
            # Show sample data
            if len(all_values) > 1:
                print("\n📋 Sample data (first row):")
                first_row = all_values[1]
                for i, value in enumerate(first_row[:5], 1):
                    print(f"   Column {i}: {value}")
            
            # Disable text wrapping
            try:
                worksheet.format(f'A1:U{end_row}', {
                    "wrapStrategy": "CLIP"
                })
                print("📄 Disabled text wrapping")
            except Exception as wrap_error:
                print(f"⚠️ Could not disable text wrapping: {wrap_error}")
            
            print(f"\n🎉 Direct paste completed successfully!")
            print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 Spreadsheet URL: https://docs.google.com/spreadsheets/d/{gsheets_service.spreadsheet_id}")
            
            return True
        else:
            print("❌ No data rows to paste")
            return False
            
    except Exception as e:
        print(f"❌ Direct paste error: {e}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")
        return False

def show_data_preview():
    """Show a preview of the data that will be pasted"""
    print("📋 Data Preview")
    print("=" * 50)
    
    try:
        all_tracker_data = firestore_service.get_all_tracker_data()
        
        if not all_tracker_data:
            print("❌ No tracker data found")
            return
        
        print(f"📊 Total trackers: {len(all_tracker_data)}")
        print("\n📋 Headers:")
        headers = [
            'Tracker Code', 'Tracking ID', 'Order ID', 'Stage', 'Status',
            'Channel', 'Courier', 'City', 'State', 'Pincode', 'Amount', 'Qty', 'Payment', 'Order Status',
            'G-Code', 'EAN-Code', 'Product SKU', 'Listing ID', 'Invoice', 'Sub Order ID', 'Last Updated'
        ]
        for i, header in enumerate(headers, 1):
            print(f"   {i:2d}. {header}")
        
        print("\n📊 Sample data (first 3 trackers):")
        sample_count = min(3, len(all_tracker_data))
        
        for i, (tracker_code, tracker_data) in enumerate(list(all_tracker_data.items())[:sample_count], 1):
            stage, current_status = get_stage_and_status(tracker_data)
            amount = tracker_data.get('amount', 0)
            formatted_amount = f"₹{amount}" if amount else "₹0"
            
            print(f"\n   {i}. {tracker_code}")
            print(f"      Tracking ID: {tracker_data.get('shipment_tracker', 'N/A')}")
            print(f"      Order ID: {tracker_data.get('order_id', 'N/A')}")
            print(f"      Stage: {stage}")
            print(f"      Status: {current_status}")
            print(f"      Amount: {formatted_amount}")
            print(f"      Channel: {tracker_data.get('channel_name', 'N/A')}")
            print(f"      Courier: {tracker_data.get('courier', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Preview error: {e}")

if __name__ == "__main__":
    print("Choose action:")
    print("1. Preview data")
    print("2. Direct paste to Google Sheets")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "1":
            show_data_preview()
        elif choice == "2":
            success = direct_paste_to_sheets()
            if success:
                print("\n🎉 Direct paste completed successfully!")
            else:
                print("\n❌ Direct paste failed!")
        else:
            print("❌ Invalid choice!")
            
    except KeyboardInterrupt:
        print("\n⏹️ Operation interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}") 