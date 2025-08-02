#!/usr/bin/env python3
"""
Simple paste script - gets exact data from frontend API and pastes without modifications
"""

import os
import sys
import requests
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.firestore_service import firestore_service
from app.services.gsheets_service import gsheets_service

def get_stage_and_status_from_flags(status):
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

def get_frontend_data():
    """Get the exact data that the frontend shows - no modifications"""
    print("📊 Getting frontend data...")
    print("=" * 50)
    
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
        
        print(f"📊 Found {len(trackers)} trackers (exact frontend data)")
        return trackers
        
    except Exception as e:
        print(f"❌ Error getting frontend data: {e}")
        return []

def simple_paste_to_sheets():
    """Simple paste - no modifications, just paste what frontend shows"""
    print("🔄 Simple Paste to Google Sheets (No Modifications)")
    print("=" * 50)
    
    try:
        # Initialize services
        print("🔧 Initializing services...")
        gsheets_service.initialize()
        
        # Get frontend data
        trackers = get_frontend_data()
        
        if not trackers:
            print("❌ No tracker data found")
            return False
        
        print(f"📊 Found {len(trackers)} trackers to paste")
        
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
        
        # Prepare all data rows - NO MODIFICATIONS
        print("📝 Preparing data rows (no modifications)...")
        all_rows = []
        
        for tracker in trackers:
            # Get details from the tracker
            details = tracker['details']
            status = tracker['status']
            
            # Calculate stage and status from boolean flags (exact frontend logic)
            stage, current_status = get_stage_and_status_from_flags(status)
            
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
            
            print(f"\n🎉 Simple paste completed successfully!")
            print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 Spreadsheet URL: https://docs.google.com/spreadsheets/d/{gsheets_service.spreadsheet_id}")
            
            return True
        else:
            print("❌ No data rows to paste")
            return False
            
    except Exception as e:
        print(f"❌ Simple paste error: {e}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")
        return False

def show_frontend_data_preview():
    """Show a preview of the frontend data"""
    print("📋 Frontend Data Preview")
    print("=" * 50)
    
    try:
        trackers = get_frontend_data()
        
        if not trackers:
            print("❌ No tracker data found")
            return
        
        print(f"📊 Total trackers: {len(trackers)}")
        print("\n📋 Headers:")
        headers = [
            'Tracker Code', 'Tracking ID', 'Order ID', 'Stage', 'Status',
            'Channel', 'Courier', 'City', 'State', 'Pincode', 'Amount', 'Qty', 'Payment', 'Order Status',
            'G-Code', 'EAN-Code', 'Product SKU', 'Listing ID', 'Invoice', 'Sub Order ID', 'Last Updated'
        ]
        for i, header in enumerate(headers, 1):
            print(f"   {i:2d}. {header}")
        
        print("\n📊 Sample data (first 3 trackers):")
        sample_count = min(3, len(trackers))
        
        for i, tracker in enumerate(trackers[:sample_count], 1):
            details = tracker['details']
            status = tracker['status']
            amount = details.get('amount', 0)
            formatted_amount = f"₹{amount}" if amount else "₹0"
            
            # Calculate stage and status from boolean flags
            stage, current_status = get_stage_and_status_from_flags(status)
            
            print(f"\n   {i}. {tracker['tracker_code']}")
            print(f"      Tracking ID: {tracker['original_tracking_id']}")
            print(f"      Order ID: {details.get('order_id', 'N/A')}")
            print(f"      Stage: {stage}")
            print(f"      Status: {current_status}")
            print(f"      Amount: {formatted_amount}")
            print(f"      Channel: {details.get('channel_name', 'N/A')}")
            print(f"      Courier: {details.get('courier', 'N/A')}")
            print(f"      Status flags: Label={status.get('label', False)}, Packing={status.get('packing', False)}, Dispatch={status.get('dispatch', False)}, Pending={status.get('pending', False)}")
        
    except Exception as e:
        print(f"❌ Preview error: {e}")

def debug_specific_trackers():
    """Debug specific trackers to see their actual status flags"""
    print("🔍 Debug Specific Trackers")
    print("=" * 50)
    
    try:
        trackers = get_frontend_data()
        
        # Trackers that should have different stages based on frontend
        target_trackers = [
            "AARO11G25037_1754113580122_1be5eaac",  # Should be Packing Pending
            "AARO11G25039_1754113580365_013533a5",  # Should be Packing Pending
            "AARO11G25044_1754113581023_1b974284",  # Should be Packing Hold
            "AARO11G25047_1754113581404_11c63dc6",  # Should be Dispatch Cancelled
            "AARO11G25048_1754113581530_8229ff25",  # Should be Packing
        ]
        
        for tracker in trackers:
            if tracker['tracker_code'] in target_trackers:
                details = tracker['details']
                status = tracker['status']
                stage, current_status = get_stage_and_status_from_flags(status)
                
                print(f"\n📊 Tracker: {tracker['tracker_code']}")
                print(f"   Tracking ID: {tracker['original_tracking_id']}")
                print(f"   Calculated Stage: {stage}")
                print(f"   Calculated Status: {current_status}")
                print(f"   Status flags: Label={status.get('label', False)}, Packing={status.get('packing', False)}, Dispatch={status.get('dispatch', False)}, Pending={status.get('pending', False)}, Cancelled={status.get('cancelled', False)}")
                
                # Show all status fields
                print(f"   All status fields: {status}")
                
    except Exception as e:
        print(f"❌ Debug error: {e}")

if __name__ == "__main__":
    print("Choose action:")
    print("1. Preview frontend data")
    print("2. Simple paste to Google Sheets (no modifications)")
    print("3. Debug specific trackers")
    
    try:
        choice = input("Enter choice (1, 2, or 3): ").strip()
        
        if choice == "1":
            show_frontend_data_preview()
        elif choice == "2":
            success = simple_paste_to_sheets()
            if success:
                print("\n🎉 Simple paste completed successfully!")
            else:
                print("\n❌ Simple paste failed!")
        elif choice == "3":
            debug_specific_trackers()
        else:
            print("❌ Invalid choice!")
            
    except KeyboardInterrupt:
        print("\n⏹️ Operation interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}") 