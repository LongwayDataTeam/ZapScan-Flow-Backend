#!/usr/bin/env python3
"""
Script to check recent data in Firestore and verify sync
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.firestore_service import firestore_service
from app.services.gsheets_service import gsheets_service

def check_recent_data():
    """Check what recent data is available and verify sync"""
    print("🔍 Checking recent data in Firestore...")
    print("=" * 50)
    
    try:
        # Get all tracker data
        all_tracker_data = firestore_service.get_all_tracker_data()
        
        if not all_tracker_data:
            print("❌ No tracker data found in Firestore")
            return
        
        print(f"📊 Total trackers in Firestore: {len(all_tracker_data)}")
        
        # Check for recent data (last 24 hours)
        now = datetime.now(timezone.utc)
        recent_trackers = []
        old_trackers = []
        
        for tracker_code, tracker_data in all_tracker_data.items():
            last_updated = tracker_data.get('last_updated', '')
            
            if last_updated:
                try:
                    # Parse the timestamp
                    if isinstance(last_updated, str):
                        # Handle different timestamp formats
                        if 'Z' in last_updated:
                            last_updated = last_updated.replace('Z', '+00:00')
                        last_updated_dt = datetime.fromisoformat(last_updated)
                    else:
                        last_updated_dt = last_updated
                    
                    # Ensure timezone info
                    if last_updated_dt.tzinfo is None:
                        last_updated_dt = last_updated_dt.replace(tzinfo=timezone.utc)
                    
                    # Check if recent (within 24 hours)
                    time_diff = now - last_updated_dt
                    if time_diff.total_seconds() < 86400:  # 24 hours
                        recent_trackers.append((tracker_code, last_updated_dt))
                    else:
                        old_trackers.append((tracker_code, last_updated_dt))
                        
                except Exception as e:
                    print(f"⚠️ Could not parse timestamp for {tracker_code}: {e}")
                    old_trackers.append((tracker_code, 'Unknown'))
            else:
                old_trackers.append((tracker_code, 'No timestamp'))
        
        print(f"📈 Recent trackers (last 24h): {len(recent_trackers)}")
        print(f"📉 Old trackers (>24h): {len(old_trackers)}")
        
        # Show sample recent trackers
        if recent_trackers:
            print("\n📝 Sample Recent Trackers:")
            for tracker_code, timestamp in recent_trackers[:5]:
                print(f"   {tracker_code}: {timestamp}")
        
        # Show sample old trackers
        if old_trackers:
            print("\n📝 Sample Old Trackers:")
            for tracker_code, timestamp in old_trackers[:5]:
                print(f"   {tracker_code}: {timestamp}")
        
        # Check Google Sheets configuration
        print("\n🔧 Google Sheets Configuration:")
        spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '1rLSCtZkVU3WJ8qQz1l5Tv3L6aaAuqf_iKGaKaLMh2zQ')
        credentials_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', 'gsheet-onescan-service.json')
        worksheet_name = os.getenv('GOOGLE_SHEETS_WORKSHEET_NAME', 'tracker')
        
        print(f"   Spreadsheet ID: {spreadsheet_id}")
        print(f"   Credentials Path: {'✅ Exists' if os.path.exists(credentials_path) else '❌ Not found'}")
        print(f"   Worksheet Name: {worksheet_name}")
        
        # Test Google Sheets sync
        print("\n🔄 Testing Google Sheets Sync with Recent Data:")
        try:
            success = gsheets_service.sync_all_tracker_data(all_tracker_data)
            if success:
                print("✅ Google Sheets sync completed successfully")
                print(f"📊 Synced {len(all_tracker_data)} trackers (including {len(recent_trackers)} recent)")
            else:
                print("❌ Google Sheets sync failed")
        except Exception as e:
            print(f"❌ Error during sync: {e}")
        
        print("\n✅ Data check completed!")
        
    except Exception as e:
        print(f"❌ Error checking data: {e}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    check_recent_data() 