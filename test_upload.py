#!/usr/bin/env python3
"""
Test script for Google Sheets upload functionality
"""

import json
from datetime import datetime
from app.services.google_sheets_service import GoogleSheetsService

def test_google_sheets_upload():
    """Test the Google Sheets upload functionality"""
    
    print("🧪 Testing Google Sheets Upload Functionality")
    print("=" * 50)
    
    # Initialize the service
    try:
        service = GoogleSheetsService()
        print("✅ Google Sheets service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return
    
    # Test data
    test_orders = [
        {
            "id": 1,
            "shipment_tracker": "TRK001",
            "order_id": "ORD001",
            "channel_name": "Amazon",
            "buyer_city": "New York",
            "buyer_state": "NY",
            "total_amount": 99.99,
            "fulfillment_status": "pending",
            "is_multi_sku": False,
            "is_multi_quantity": False,
            "total_items": 1,
            "created_at": datetime.now().isoformat()
        },
        {
            "id": 2,
            "shipment_tracker": "TRK002",
            "order_id": "ORD002",
            "channel_name": "eBay",
            "buyer_city": "Los Angeles",
            "buyer_state": "CA",
            "total_amount": 149.99,
            "fulfillment_status": "pending",
            "is_multi_sku": True,
            "is_multi_quantity": False,
            "total_items": 2,
            "created_at": datetime.now().isoformat()
        }
    ]
    
    print(f"\n📤 Testing upload of {len(test_orders)} orders...")
    
    # Test upload
    try:
        result = service.upload_orders_to_sheets(test_orders)
        
        if result["success"]:
            print(f"✅ Upload successful!")
            print(f"   Records uploaded: {result['records_uploaded']}")
            print(f"   Sheet name: {result['sheet_name']}")
            print(f"   Message: {result['message']}")
        else:
            print(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
    
    # Test status check
    print(f"\n📊 Testing status check...")
    try:
        status = service.get_workflow_status()
        print(f"✅ Status check successful!")
        print(f"   Total orders: {status['total_orders']}")
        print(f"   Total scans: {status['total_scans']}")
        print(f"   Data size: {status['data_size_mb']:.2f} MB")
        print(f"   Can clear: {status['can_clear']}")
        
    except Exception as e:
        print(f"❌ Status check failed: {e}")
    
    # Test sheets info
    print(f"\n📋 Testing sheets info...")
    try:
        # Get current data from Scan Processor tab
        data = service.get_sheet_data(service.processor_tab)
        print(f"✅ Sheets info successful!")
        print(f"   Spreadsheet ID: {service.spreadsheet_id}")
        print(f"   Processor Tab: {service.processor_tab}")
        print(f"   Database Tab: {service.database_tab}")
        print(f"   Current rows in processor: {len(data)}")
        
        if len(data) > 0:
            print(f"   Headers: {data[0] if data else 'No data'}")
            print(f"   Data rows: {len(data) - 1}")
        
    except Exception as e:
        print(f"❌ Sheets info failed: {e}")
    
    print(f"\n🎯 Test completed!")

if __name__ == "__main__":
    test_google_sheets_upload() 