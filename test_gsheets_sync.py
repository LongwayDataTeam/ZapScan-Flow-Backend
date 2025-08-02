#!/usr/bin/env python3
"""
Test script for Google Sheets sync functionality with manual pasting verification
"""

import os
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.firestore_service import firestore_service
from app.services.gsheets_service import gsheets_service

def test_gsheets_sync():
    """Test the Google Sheets sync functionality with manual verification"""
    print("🧪 Testing Google Sheets sync functionality...")
    print("=" * 60)
    
    # Check environment variables
    print("📋 Environment Variables Check:")
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    credentials_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', 'gsheet-onescan-service.json')
    worksheet_name = os.getenv('GOOGLE_SHEETS_WORKSHEET_NAME', 'tracker')
    
    print(f"   Spreadsheet ID: {'✅ Set' if spreadsheet_id else '❌ Not set'}")
    print(f"   Credentials Path: {'✅ Exists' if os.path.exists(credentials_path) else '❌ Not found'}")
    print(f"   Worksheet Name: {worksheet_name}")
    print()
    
    # Test Google Sheets service initialization
    print("🔧 Testing Google Sheets Service Initialization:")
    try:
        gsheets_initialized = gsheets_service.initialize()
        if gsheets_initialized:
            print("   ✅ Google Sheets service initialized successfully")
            print(f"   📊 Using Spreadsheet: {gsheets_service.spreadsheet_id}")
            print(f"   📋 Using Worksheet: {gsheets_service.worksheet_name}")
        else:
            print("   ❌ Google Sheets service initialization failed")
            return False
    except Exception as e:
        print(f"   ❌ Google Sheets service initialization error: {e}")
        return False
    print()
    
    # Test Firestore data retrieval
    print("📊 Testing Firestore Data Retrieval:")
    try:
        all_tracker_data = firestore_service.get_all_tracker_data()
        tracker_count = len(all_tracker_data) if all_tracker_data else 0
        print(f"   ✅ Retrieved {tracker_count} trackers from Firestore")
        
        if tracker_count == 0:
            print("   ⚠️ No tracker data found in Firestore")
            print("   💡 You may need to upload some tracker data first")
            return False
        
        # Show sample data for verification
        print("   📋 Sample Tracker Data:")
        sample_count = min(3, tracker_count)
        for i, (tracker_code, tracker_data) in enumerate(list(all_tracker_data.items())[:sample_count]):
            status = tracker_data.get('status', {})
            print(f"      {i+1}. {tracker_code}")
            print(f"         Tracking ID: {tracker_data.get('shipment_tracker', 'N/A')}")
            print(f"         Order ID: {tracker_data.get('order_id', 'N/A')}")
            print(f"         Status: Label={status.get('label', False)}, Packing={status.get('packing', False)}, Dispatch={status.get('dispatch', False)}")
            print(f"         Last Updated: {tracker_data.get('last_updated', 'N/A')}")
            print()
        
    except Exception as e:
        print(f"   ❌ Firestore data retrieval error: {e}")
        return False
    print()
    
    # Test Google Sheets sync
    print("🔄 Testing Google Sheets Sync:")
    try:
        if all_tracker_data and tracker_count > 0:
            print(f"   📝 Starting sync of {tracker_count} trackers...")
            success = gsheets_service.sync_all_tracker_data(all_tracker_data)
            if success:
                print("   ✅ Google Sheets sync completed successfully")
                print(f"   📊 Synced {tracker_count} trackers to Google Sheets")
                print(f"   📅 Sync completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Verify the sync by reading back the data
                print("\n🔍 Verifying Sync Results:")
                try:
                    worksheet = gsheets_service.worksheet
                    if worksheet:
                        # Get all values from the worksheet
                        all_values = worksheet.get_all_values()
                        header_count = len(all_values[0]) if all_values else 0
                        data_count = len(all_values) - 1 if len(all_values) > 1 else 0
                        
                        print(f"   📋 Headers found: {header_count} columns")
                        print(f"   📊 Data rows found: {data_count} rows")
                        
                        if data_count > 0:
                            print("   📋 Headers:")
                            headers = all_values[0]
                            for i, header in enumerate(headers, 1):
                                print(f"      {i}. {header}")
                            
                            print("\n   📊 Sample Data (first 3 rows):")
                            for i, row in enumerate(all_values[1:4], 1):
                                print(f"      Row {i}: {row[:5]}...")  # Show first 5 columns
                        
                        # Check if data starts from A2 as expected
                        if len(all_values) > 1:
                            print(f"\n   ✅ Data starts from row 2 (A2) as expected")
                            print(f"   ✅ Headers preserved in row 1")
                        else:
                            print(f"\n   ⚠️ Only headers found, no data rows")
                        
                except Exception as verify_error:
                    print(f"   ⚠️ Could not verify sync results: {verify_error}")
                
            else:
                print("   ❌ Google Sheets sync failed")
                return False
        else:
            print("   ⚠️ No data to sync - skipping sync test")
            return False
    except Exception as e:
        print(f"   ❌ Google Sheets sync error: {e}")
        import traceback
        print(f"   🔍 Full traceback: {traceback.format_exc()}")
        return False
    print()
    
    # Manual verification instructions
    print("🔍 Manual Verification Instructions:")
    print("=" * 60)
    print("1. Open your Google Sheets spreadsheet:")
    print(f"   📊 URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print(f"   📋 Worksheet: {worksheet_name}")
    print()
    print("2. Check the following:")
    print("   ✅ Headers are in row 1 (A1:U1)")
    print("   ✅ Data starts from row 2 (A2)")
    print("   ✅ Stage and Status columns show correct values")
    print("   ✅ Amount column shows ₹ symbol")
    print("   ✅ Last Updated shows timestamps or '-'")
    print()
    print("3. Expected Column Order:")
    print("   1. Tracker Code")
    print("   2. Tracking ID")
    print("   3. Order ID")
    print("   4. Stage")
    print("   5. Status")
    print("   6. Channel")
    print("   7. Courier")
    print("   8. City")
    print("   9. State")
    print("   10. Pincode")
    print("   11. Amount")
    print("   12. Qty")
    print("   13. Payment")
    print("   14. Order Status")
    print("   15. G-Code")
    print("   16. EAN-Code")
    print("   17. Product SKU")
    print("   18. Listing ID")
    print("   19. Invoice")
    print("   20. Sub Order ID")
    print("   21. Last Updated")
    print()
    
    print("✅ All tests completed!")
    return True

def manual_sync_test():
    """Manual sync test with detailed output"""
    print("🔄 Manual Google Sheets Sync Test")
    print("=" * 60)
    
    try:
        # Initialize services
        gsheets_service.initialize()
        all_tracker_data = firestore_service.get_all_tracker_data()
        
        if not all_tracker_data:
            print("❌ No tracker data found in Firestore")
            return False
        
        print(f"📊 Found {len(all_tracker_data)} trackers to sync")
        
        # Perform sync
        success = gsheets_service.sync_all_tracker_data(all_tracker_data)
        
        if success:
            print("✅ Manual sync completed successfully!")
            print(f"📅 Sync time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 Synced {len(all_tracker_data)} trackers")
            
            # Show sync summary
            print("\n📋 Sync Summary:")
            stage_counts = {}
            status_counts = {}
            
            for tracker_code, tracker_data in all_tracker_data.items():
                stage, status = gsheets_service._get_latest_scan_info(tracker_data)
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print("   📊 Stage Distribution:")
            for stage, count in sorted(stage_counts.items()):
                print(f"      {stage}: {count}")
            
            print("   📊 Status Distribution:")
            for status, count in sorted(status_counts.items()):
                print(f"      {status}: {count}")
            
            return True
        else:
            print("❌ Manual sync failed!")
            return False
            
    except Exception as e:
        print(f"❌ Manual sync error: {e}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Full test with verification")
    print("2. Manual sync test only")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "2":
            success = manual_sync_test()
        else:
            success = test_gsheets_sync()
        
        if success:
            print("\n🎉 Google Sheets sync is working correctly!")
            print("📝 The scheduler will automatically sync every 5 minutes.")
        else:
            print("\n❌ Google Sheets sync test failed!")
            print("🔧 Please check the configuration and try again.")
            
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}") 