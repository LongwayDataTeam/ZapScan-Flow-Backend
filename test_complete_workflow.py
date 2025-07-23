#!/usr/bin/env python3
"""
Test script for Google Sheets workflow
Tests connection, upload, scanning, and data management
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_connection():
    """Test Google Sheets connection"""
    print("🔗 Testing Google Sheets connection...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/sheets-workflow/test-connection")
        data = response.json()
        
        if data.get("connected"):
            print("✅ Google Sheets connection successful")
            print(f"📊 Spreadsheet ID: {data.get('spreadsheet_id')}")
            print(f"📋 Processor Tab: {data.get('processor_tab')}")
            print(f"🗄️ Database Tab: {data.get('database_tab')}")
            return True
        else:
            print(f"❌ Google Sheets connection failed: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_upload():
    """Test data upload to Google Sheets"""
    print("\n📤 Testing data upload...")
    
    try:
        # Test JSON upload
        test_data = {
            "orders": [
                {
                    "id": 1,
                    "order_id": "TEST001",
                    "sub_order_id": "SUB001",
                    "shipment_tracker": "TRACK001",
                    "courier": "Test Courier",
                    "channel_name": "Test Channel",
                    "g_code": "GC000001",
                    "ean_code": "EAN0000000001",
                    "product_sku_code": "SKU000001",
                    "channel_listing_id": "LIST000001",
                    "qty": 1,
                    "amount": 100.00,
                    "payment_mode": "PREPAID",
                    "order_status": "pending",
                    "buyer_city": "Test City",
                    "buyer_state": "Test State",
                    "buyer_pincode": "123456",
                    "invoice_number": "INV000001"
                },
                {
                    "id": 2,
                    "order_id": "TEST002",
                    "sub_order_id": "SUB002",
                    "shipment_tracker": "TRACK002",
                    "courier": "Test Courier",
                    "channel_name": "Test Channel",
                    "g_code": "GC000002",
                    "ean_code": "EAN0000000002",
                    "product_sku_code": "SKU000002",
                    "channel_listing_id": "LIST000002",
                    "qty": 2,
                    "amount": 200.00,
                    "payment_mode": "PREPAID",
                    "order_status": "pending",
                    "buyer_city": "Test City",
                    "buyer_state": "Test State",
                    "buyer_pincode": "123456",
                    "invoice_number": "INV000002"
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/sheets-workflow/upload-json",
            json=test_data
        )
        data = response.json()
        
        if data.get("success"):
            print("✅ Data upload successful")
            print(f"📊 Orders uploaded: {data.get('orders_uploaded')}")
            return True
        else:
            print(f"❌ Data upload failed: {data}")
            return False
            
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        return False

def test_scanning():
    """Test scanning functionality"""
    print("\n🔍 Testing scanning functionality...")
    
    try:
        # Test scanning with TRACK001
        response = requests.get(f"{BASE_URL}/api/v1/sheets-workflow/test-scan/TRACK001")
        data = response.json()
        
        if data.get("test_passed"):
            print("✅ Scanning test successful")
            print(f"📊 Trackers found: {data.get('trackers_found')}")
            print(f"🔍 Tracking ID: {data.get('tracking_id')}")
            return True
        else:
            print(f"❌ Scanning test failed: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Scanning test failed: {e}")
        return False

def test_scan_endpoints():
    """Test actual scan endpoints"""
    print("\n📱 Testing scan endpoints...")
    
    try:
        # Test label scan
        scan_data = {"tracker_code": "TRACK001", "scan_type": "label"}
        response = requests.post(f"{BASE_URL}/api/v1/scan/label/", json=scan_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Label scan successful")
            print(f"📊 Trackers scanned: {data.get('total_scanned')}")
        else:
            print(f"❌ Label scan failed: {response.text}")
            return False
        
        # Test packing scan
        scan_data = {"tracker_code": "TRACK001", "scan_type": "packing"}
        response = requests.post(f"{BASE_URL}/api/v1/scan/packing/", json=scan_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Packing scan successful")
            print(f"📊 Trackers scanned: {data.get('total_scanned')}")
        else:
            print(f"❌ Packing scan failed: {response.text}")
            return False
        
        # Test dispatch scan
        scan_data = {"tracker_code": "TRACK001", "scan_type": "dispatch"}
        response = requests.post(f"{BASE_URL}/api/v1/scan/dispatch/", json=scan_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Dispatch scan successful")
            print(f"📊 Trackers scanned: {data.get('total_scanned')}")
        else:
            print(f"❌ Dispatch scan failed: {response.text}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Scan endpoints test failed: {e}")
        return False

def test_clear_functionality():
    """Test clear and move to database functionality"""
    print("\n🗑️ Testing clear functionality...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/sheets-workflow/clear")
        data = response.json()
        
        if data.get("success"):
            print("✅ Clear functionality successful")
            print(f"📊 Records moved: {data.get('moved_records', 0)}")
            print(f"📋 Source tab: {data.get('source_tab')}")
            print(f"🗄️ Destination tab: {data.get('destination_tab')}")
            return True
        else:
            print(f"❌ Clear functionality failed: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Clear test failed: {e}")
        return False

def test_status():
    """Test status endpoints"""
    print("\n📊 Testing status endpoints...")
    
    try:
        # Test workflow status
        response = requests.get(f"{BASE_URL}/api/v1/sheets-workflow/status")
        data = response.json()
        
        print("✅ Workflow status retrieved")
        print(f"📊 Processor tab data: {data.get('processor_tab_data', 0)}")
        print(f"🗄️ Database tab data: {data.get('database_tab_data', 0)}")
        
        # Test sheets info
        response = requests.get(f"{BASE_URL}/api/v1/sheets-workflow/sheets-info")
        data = response.json()
        
        if data.get("connected"):
            print("✅ Sheets info retrieved")
            print(f"📋 Headers: {data.get('processor_header_count', 0)}")
        else:
            print(f"❌ Sheets info failed: {data.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Status test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Google Sheets Workflow Test Suite")
    print("=" * 50)
    
    tests = [
        ("Connection", test_connection),
        ("Upload", test_upload),
        ("Scanning", test_scanning),
        ("Scan Endpoints", test_scan_endpoints),
        ("Status", test_status),
        ("Clear", test_clear_functionality)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📋 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Google Sheets workflow is working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the configuration and try again.")

if __name__ == "__main__":
    main() 