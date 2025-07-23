#!/usr/bin/env python3
"""
Test script for simple backend Google Sheets upload
"""

import requests
import json

def test_google_sheets_upload():
    """Test the Google Sheets upload functionality"""
    
    print("🧪 Testing Google Sheets Upload via API")
    print("=" * 50)
    
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
            "created_at": "2025-07-23T12:00:00"
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
            "created_at": "2025-07-23T12:00:00"
        }
    ]
    
    print(f"📤 Testing upload of {len(test_orders)} orders...")
    
    try:
        # Test JSON upload
        response = requests.post(
            'http://localhost:8000/api/v1/sheets-workflow/upload-json',
            json={"orders": test_orders},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful!")
            print(f"   Message: {result.get('message', 'No message')}")
            print(f"   Total orders: {result.get('total_orders', 0)}")
            print(f"   Processed orders: {result.get('processed_orders', 0)}")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
    
    # Test status check
    print(f"\n📊 Testing status check...")
    try:
        response = requests.get('http://localhost:8000/api/v1/sheets-workflow/status')
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Status check successful!")
            print(f"   Total orders: {status.get('total_orders', 0)}")
            print(f"   Total scans: {status.get('total_scans', 0)}")
            print(f"   Data size: {status.get('data_size_mb', 0):.2f} MB")
            print(f"   Can clear: {status.get('can_clear', False)}")
        else:
            print(f"❌ Status check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Status check failed: {e}")
    
    print(f"\n🎯 Test completed!")

if __name__ == "__main__":
    test_google_sheets_upload() 