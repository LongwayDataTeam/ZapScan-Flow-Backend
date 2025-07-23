#!/usr/bin/env python3
"""
Daily Data Export and Cleanup Scheduler
Automatically exports daily scan data to Google Sheets and cleans up database
"""

import os
import sys
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.services.data_export_service import DataExportService


def daily_export_and_cleanup():
    """Daily job to export data and cleanup database"""
    print(f"🕐 Starting daily export and cleanup at {datetime.now()}")
    
    try:
        db = SessionLocal()
        export_service = DataExportService()
        
        # Get yesterday's date
        yesterday = datetime.now().date() - timedelta(days=1)
        
        # First, get summary of data to be exported
        summary = export_service.get_daily_summary(db, yesterday)
        print(f"📊 Data summary for {yesterday}:")
        print(f"   - Orders: {summary['total_orders']}")
        print(f"   - Scans: {summary['total_scans']}")
        print(f"   - Data size: {summary['data_size_mb']:.2f} MB")
        
        if summary['total_orders'] == 0:
            print("✅ No data to export for yesterday")
            return
        
        # Export data to Google Sheets
        print("📤 Exporting data to Google Sheets...")
        export_result = export_service.export_daily_data_to_sheets(db, yesterday)
        
        if export_result["success"]:
            print(f"✅ Export successful: {export_result['records_exported']} records")
            
            # Cleanup database
            print("🧹 Cleaning up database...")
            cleanup_result = export_service.cleanup_daily_data(db, yesterday)
            
            if cleanup_result["success"]:
                print(f"✅ Cleanup successful:")
                print(f"   - Deleted orders: {cleanup_result['deleted_orders']}")
                print(f"   - Deleted sessions: {cleanup_result['deleted_sessions']}")
            else:
                print(f"❌ Cleanup failed: {cleanup_result['error']}")
        else:
            print(f"❌ Export failed: {export_result['error']}")
            
    except Exception as e:
        print(f"❌ Daily job failed: {e}")
    finally:
        db.close()


def setup_scheduler():
    """Setup the daily scheduler"""
    print("⏰ Setting up daily scheduler...")
    
    # Schedule daily job at 2:00 AM
    schedule.every().day.at("02:00").do(daily_export_and_cleanup)
    
    print("✅ Scheduler configured to run daily at 2:00 AM")
    print("📊 Daily job will:")
    print("   1. Export yesterday's data to Google Sheets")
    print("   2. Clean up database to free space")
    print("   3. Keep only current day's data in database")


def run_scheduler():
    """Run the scheduler"""
    setup_scheduler()
    
    print("🚀 Starting scheduler...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n⏹️ Scheduler stopped")


def run_manual_export(date_str: str = None):
    """Run manual export for a specific date"""
    print("🔧 Running manual export...")
    
    try:
        db = SessionLocal()
        export_service = DataExportService()
        
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                print("❌ Invalid date format. Use YYYY-MM-DD")
                return
        else:
            target_date = datetime.now().date() - timedelta(days=1)
        
        print(f"📊 Exporting data for {target_date}...")
        
        # Export
        export_result = export_service.export_daily_data_to_sheets(db, target_date)
        if export_result["success"]:
            print(f"✅ Export successful: {export_result['records_exported']} records")
            
            # Ask for cleanup
            cleanup_choice = input("🧹 Do you want to cleanup database? (y/n): ").lower()
            if cleanup_choice == 'y':
                cleanup_result = export_service.cleanup_daily_data(db, target_date)
                if cleanup_result["success"]:
                    print(f"✅ Cleanup successful: {cleanup_result['deleted_orders']} orders deleted")
                else:
                    print(f"❌ Cleanup failed: {cleanup_result['error']}")
        else:
            print(f"❌ Export failed: {export_result['error']}")
            
    except Exception as e:
        print(f"❌ Manual export failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Daily Data Export Scheduler")
    parser.add_argument("--manual", help="Run manual export for specific date (YYYY-MM-DD)")
    parser.add_argument("--scheduler", action="store_true", help="Run the scheduler")
    
    args = parser.parse_args()
    
    if args.manual:
        run_manual_export(args.manual)
    elif args.scheduler:
        run_scheduler()
    else:
        print("Usage:")
        print("  python daily_cleanup_scheduler.py --manual 2024-01-15")
        print("  python daily_cleanup_scheduler.py --scheduler") 