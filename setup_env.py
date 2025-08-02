#!/usr/bin/env python3
"""
Setup script for Google Sheets environment variables
"""

import os
import sys

def setup_environment():
    """Setup environment variables for Google Sheets sync"""
    print("🔧 Setting up Google Sheets environment variables...")
    print("=" * 50)
    
    # Check current environment variables
    print("📋 Current Environment Variables:")
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    credentials_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', 'gsheet-onescan-service.json')
    worksheet_name = os.getenv('GOOGLE_SHEETS_WORKSHEET_NAME', 'tracker')
    
    print(f"   GOOGLE_SHEETS_SPREADSHEET_ID: {'✅ Set' if spreadsheet_id else '❌ Not set'}")
    print(f"   GOOGLE_SHEETS_CREDENTIALS_PATH: {'✅ Exists' if os.path.exists(credentials_path) else '❌ Not found'}")
    print(f"   GOOGLE_SHEETS_WORKSHEET_NAME: {worksheet_name}")
    
    # Check if credentials file exists
    if not os.path.exists(credentials_path):
        print(f"\n❌ Credentials file not found: {credentials_path}")
        print("💡 Please ensure the Google Sheets service account JSON file is in the project root")
        return False
    
    # If spreadsheet ID is not set, prompt user
    if not spreadsheet_id:
        print("\n❌ GOOGLE_SHEETS_SPREADSHEET_ID is not set!")
        print("💡 To fix this, you need to:")
        print("   1. Create a Google Spreadsheet")
        print("   2. Share it with your service account email")
        print("   3. Copy the Spreadsheet ID from the URL")
        print("   4. Set the environment variable")
        
        # Try to get from user
        try:
            user_spreadsheet_id = input("\n📝 Enter your Google Spreadsheet ID (or press Enter to skip): ").strip()
            if user_spreadsheet_id:
                # Set environment variable for current session
                os.environ['GOOGLE_SHEETS_SPREADSHEET_ID'] = user_spreadsheet_id
                print(f"✅ Set GOOGLE_SHEETS_SPREADSHEET_ID to: {user_spreadsheet_id}")
                
                # Also save to .env file
                env_file = '.env'
                with open(env_file, 'a') as f:
                    f.write(f"\nGOOGLE_SHEETS_SPREADSHEET_ID={user_spreadsheet_id}\n")
                print(f"💾 Saved to {env_file} file")
                
                return True
            else:
                print("⚠️ Skipping spreadsheet ID setup")
                return False
        except KeyboardInterrupt:
            print("\n⚠️ Setup cancelled")
            return False
    
    print("\n✅ Environment variables are properly configured!")
    return True

def test_connection():
    """Test the Google Sheets connection"""
    print("\n🧪 Testing Google Sheets connection...")
    
    try:
        from app.services.gsheets_service import gsheets_service
        
        # Initialize the service
        if gsheets_service.initialize():
            print("✅ Google Sheets service initialized successfully")
            
            # Test spreadsheet access
            spreadsheet = gsheets_service.sheets_service.open_by_key(gsheets_service.spreadsheet_id)
            print(f"✅ Successfully accessed spreadsheet: {spreadsheet.title}")
            
            # Test worksheet access
            try:
                worksheet = spreadsheet.worksheet(gsheets_service.worksheet_name)
                print(f"✅ Successfully accessed worksheet: {gsheets_service.worksheet_name}")
                
                # Get current data
                all_values = worksheet.get_all_values()
                print(f"📊 Current data in sheet: {len(all_values)} rows")
        
        return True
            except Exception as e:
                print(f"❌ Could not access worksheet: {e}")
                return False
        else:
            print("❌ Failed to initialize Google Sheets service")
            return False
        
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Google Sheets Environment Setup")
    print("=" * 50)
    
    # Setup environment
    if setup_environment():
        # Test connection
        if test_connection():
            print("\n🎉 Setup completed successfully!")
            print("📝 Your Google Sheets sync should now work properly.")
        else:
            print("\n❌ Connection test failed!")
            print("🔧 Please check your credentials and spreadsheet permissions.")
    else:
        print("\n⚠️ Setup incomplete!")
        print("🔧 Please configure the environment variables manually.") 