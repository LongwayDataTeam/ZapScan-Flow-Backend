#!/usr/bin/env python3
"""
Test script to verify stage and status logic matches frontend
"""
import os
import sys
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.services.gsheets_service import gsheets_service

def test_stage_status_logic():
    """Test the stage and status logic with sample data"""
    
    # Sample tracker data with different status combinations
    test_cases = [
        {
            "name": "Not Started",
            "status": {"label": False, "packing": False, "dispatch": False, "pending": False, "cancelled": False},
            "expected_stage": "Label",
            "expected_status": "Label yet to Scan"
        },
        {
            "name": "Label Scanned",
            "status": {"label": True, "packing": False, "dispatch": False, "pending": False, "cancelled": False},
            "expected_stage": "Packing Pending",
            "expected_status": "Packing Pending Shipment"
        },
        {
            "name": "Packing Scanned",
            "status": {"label": True, "packing": True, "dispatch": False, "pending": False, "cancelled": False},
            "expected_stage": "Packing",
            "expected_status": "Packing Scanned"
        },
        {
            "name": "Dispatch Scanned",
            "status": {"label": True, "packing": True, "dispatch": True, "pending": False, "cancelled": False},
            "expected_stage": "Dispatch",
            "expected_status": "Dispatched"
        },
        {
            "name": "Packing Hold",
            "status": {"label": True, "packing": False, "dispatch": False, "pending": True, "cancelled": False},
            "expected_stage": "Packing Hold",
            "expected_status": "Packing Hold"
        },
        {
            "name": "Dispatch Pending",
            "status": {"label": True, "packing": True, "dispatch": False, "pending": True, "cancelled": False},
            "expected_stage": "Dispatch Pending",
            "expected_status": "Dispatch Pending"
        },
        {
            "name": "Cancelled",
            "status": {"label": True, "packing": True, "dispatch": False, "pending": False, "cancelled": True},
            "expected_stage": "Dispatch Cancelled",
            "expected_status": "Cancelled"
        }
    ]
    
    print("🧪 Testing Stage and Status Logic")
    print("=" * 50)
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"   Status: {test_case['status']}")
        
        # Create mock tracker data
        tracker_data = {
            "status": test_case["status"],
            "tracker_code": f"TEST{i}",
            "shipment_tracker": f"TRACK{i}",
            "order_id": f"ORDER{i}",
            "channel_name": "Test Channel",
            "courier": "Test Courier",
            "buyer_city": "Test City",
            "buyer_state": "Test State",
            "buyer_pincode": "123456",
            "amount": 1000,
            "qty": 1,
            "payment_mode": "COD",
            "order_status": "Shipped",
            "g_code": f"GCODE{i}",
            "ean_code": f"EAN{i}",
            "product_sku_code": f"SKU{i}",
            "channel_listing_id": f"LISTING{i}",
            "invoice_number": f"INV{i}",
            "sub_order_id": f"SUB{i}",
            "last_updated": datetime.now().isoformat()
        }
        
        # Get stage and status using our logic
        stage, status = gsheets_service._get_latest_scan_info(tracker_data)
        
        # Check if results match expected
        stage_correct = stage == test_case["expected_stage"]
        status_correct = status == test_case["expected_status"]
        
        print(f"   Expected Stage: {test_case['expected_stage']}")
        print(f"   Actual Stage:   {stage}")
        print(f"   Expected Status: {test_case['expected_status']}")
        print(f"   Actual Status:   {status}")
        
        if stage_correct and status_correct:
            print("   ✅ PASS")
        else:
            print("   ❌ FAIL")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Stage and Status logic is correct.")
    else:
        print("❌ Some tests failed. Please check the logic.")
    
    return all_passed

if __name__ == "__main__":
    success = test_stage_status_logic()
    if success:
        print("\n✅ Stage and Status logic matches frontend expectations!")
    else:
        print("\n❌ Stage and Status logic needs adjustment!") 