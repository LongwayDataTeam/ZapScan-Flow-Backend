#!/usr/bin/env python3
"""
Test script for scanning APIs
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_platform_statistics():
    """Test platform statistics API"""
    print("🔍 Testing Platform Statistics API...")
    
    for scan_type in ["label", "packing", "dispatch"]:
        try:
            response = requests.get(f"{BASE_URL}/api/v1/scan/statistics/platform?scan_type={scan_type}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {scan_type.capitalize()} Statistics: {len(data)} couriers found")
                for stat in data[:3]:  # Show first 3
                    print(f"   - {stat['courier']}: {stat['total']} total, {stat['scanned']} scanned")
            else:
                print(f"❌ {scan_type.capitalize()} Statistics failed: {response.status_code}")
        except Exception as e:
            print(f"❌ {scan_type.capitalize()} Statistics error: {e}")

def test_recent_scans():
    """Test recent scans API"""
    print("\n🔍 Testing Recent Scans API...")
    
    for scan_type in ["label", "packing", "dispatch"]:
        try:
            response = requests.get(f"{BASE_URL}/api/v1/scan/recent/{scan_type}?page=1&limit=5")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {scan_type.capitalize()} Recent Scans: {data['count']} total, {len(data['results'])} shown")
                for scan in data['results'][:2]:  # Show first 2
                    print(f"   - {scan['tracking_id']}: {scan['scan_status']} at {scan['scan_time']}")
            else:
                print(f"❌ {scan_type.capitalize()} Recent Scans failed: {response.status_code}")
        except Exception as e:
            print(f"❌ {scan_type.capitalize()} Recent Scans error: {e}")

def test_tracker_apis():
    """Test tracker-related APIs"""
    print("\n🔍 Testing Tracker APIs...")
    
    # Test tracker count
    try:
        response = requests.get(f"{BASE_URL}/api/v1/tracker/TRK001234567/count")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Tracker Count: {data['total']} total, {data['label']} label, {data['packing']} packing, {data['dispatch']} dispatch")
        else:
            print(f"❌ Tracker Count failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Tracker Count error: {e}")
    
    # Test all trackers
    try:
        response = requests.get(f"{BASE_URL}/api/v1/trackers/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ All Trackers: {len(data['trackers'])} trackers found")
        else:
            print(f"❌ All Trackers failed: {response.status_code}")
    except Exception as e:
        print(f"❌ All Trackers error: {e}")

def test_google_sheets_status():
    """Test Google Sheets status"""
    print("\n🔍 Testing Google Sheets Status...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/sheets-workflow/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Google Sheets Status: {data['total_orders']} orders, {data['total_scans']} scans")
        else:
            print(f"❌ Google Sheets Status failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Google Sheets Status error: {e}")

if __name__ == "__main__":
    print("🚀 Testing Scanning APIs...")
    print("=" * 50)
    
    test_platform_statistics()
    test_recent_scans()
    test_tracker_apis()
    test_google_sheets_status()
    
    print("\n" + "=" * 50)
    print("✅ Testing complete!") 