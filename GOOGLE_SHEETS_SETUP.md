# Google Sheets Integration Setup

This guide will help you set up the Google Sheets integration for automatic data synchronization every 5 minutes.

## 🔧 Prerequisites

1. **Google Cloud Project** with Google Sheets API enabled
2. **Service Account** with Google Sheets permissions
3. **Google Spreadsheet** for data storage

## 📋 Setup Steps

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the **Google Sheets API** and **Google Drive API**

### 2. Create Service Account

1. In Google Cloud Console, go to **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Give it a name like `onescan-gsheets-service`
4. Grant **Editor** role to the service account
5. Create and download the JSON key file

### 3. Set Up Google Spreadsheet

1. Create a new Google Spreadsheet
2. Share it with your service account email (found in the JSON key file)
3. Give **Editor** permissions to the service account
4. Copy the Spreadsheet ID from the URL

### 4. Configure Environment Variables

Add these environment variables to your `.env` file:

```bash
# Google Sheets Configuration
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
GOOGLE_SHEETS_CREDENTIALS_PATH=gsheet-onescan-service.json
GOOGLE_SHEETS_WORKSHEET_NAME=tracker
```

### 5. Place Credentials File

1. Rename your downloaded service account JSON file to `gsheet-onescan-service.json`
2. Place it in the root directory of your backend project

## 🧪 Testing the Setup

Run the test script to verify your setup:

```bash
python test_gsheets_sync.py
```

## 🔄 Automatic Sync

The system automatically syncs data to Google Sheets every 5 minutes with the following features:

- **Override Mode**: Completely replaces all data in the sheet
- **Real-time Updates**: Syncs all tracker data from Firestore
- **Error Handling**: Retries on failures
- **Logging**: Detailed logs for monitoring

## 📊 Data Structure

The Google Sheet will contain the following columns:

| Column | Description |
|--------|-------------|
| Tracker Code | Unique tracker identifier |
| Tracking ID | Shipment tracking number |
| Channel ID | Platform channel ID |
| Order ID | Order identifier |
| Sub Order ID | Sub-order identifier |
| Stage | Current scan stage (Label/Packing/Dispatch/Cancelled) |
| Status | Current status |
| Courier | Delivery courier |
| Channel Name | Platform name |
| G-Code | Product G-Code |
| EAN-Code | Product EAN code |
| Product SKU | Product SKU code |
| Channel Listing ID | Platform listing ID |
| Quantity | Order quantity |
| Amount | Order amount |
| Payment Mode | Payment method |
| Order Status | Order status |
| Buyer City | Buyer's city |
| Buyer State | Buyer's state |
| Buyer Pincode | Buyer's pincode |
| Invoice Number | Invoice number |
| Last Updated | Last update timestamp |
| Sync Timestamp | Sync completion time |

## 🚀 Manual Sync Endpoints

### Check Sync Status
```bash
GET /api/v1/sync/gsheets/status
```

### Trigger Manual Sync
```bash
POST /api/v1/sync/gsheets/manual
```

## 🔍 Troubleshooting

### Common Issues

1. **"Google Sheets credentials not found"**
   - Ensure `gsheet-onescan-service.json` is in the project root
   - Check file permissions

2. **"Cannot access spreadsheet"**
   - Verify the service account has Editor permissions
   - Check the Spreadsheet ID is correct

3. **"No tracker data to sync"**
   - Upload some tracker data first
   - Check Firestore connection

4. **"Authentication error"**
   - Verify the service account JSON is valid
   - Check API is enabled in Google Cloud Console

### Debug Commands

```bash
# Test the setup
python test_gsheets_sync.py

# Check environment variables
echo $GOOGLE_SHEETS_SPREADSHEET_ID
echo $GOOGLE_SHEETS_CREDENTIALS_PATH

# Check if credentials file exists
ls -la gsheet-onescan-service.json
```

## 📝 Monitoring

The system provides detailed logging:

- ✅ Successful syncs with timestamp
- ❌ Error messages with full traceback
- 📊 Number of trackers synced
- 🔄 Sync cycle information

Check the application logs to monitor sync status. 