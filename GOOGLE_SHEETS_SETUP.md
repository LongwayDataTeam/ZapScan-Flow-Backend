# Google Sheets Integration Setup

This guide explains how to set up Google Sheets integration for automatic data synchronization.

## Prerequisites

1. **Google Cloud Project**: You need a Google Cloud Project with the Google Sheets API enabled
2. **Service Account**: Create a service account with appropriate permissions
3. **Google Sheets**: Create a Google Sheets document for data storage

## Setup Steps

### 1. Enable Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to "APIs & Services" > "Library"
4. Search for "Google Sheets API" and enable it

### 2. Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in the service account details
4. Download the JSON credentials file
5. Rename it to `credentials.json` and place it in the backend root directory

### 3. Set Up Google Sheets

1. Create a new Google Sheets document
2. Copy the spreadsheet ID from the URL (the long string between `/d/` and `/edit`)
3. Create a worksheet named "tracker" (or update the environment variable)

**Current Configuration:**
- Spreadsheet ID: `1rLSCtZkVU3WJ8qQz1l5Tv3L6aaAuqf_iKGaKaLMh2zQ`
- Worksheet Name: `tracker`
- Credentials File: `gsheet-onescan-service.json`

### 4. Configure Environment Variables

Add these environment variables to your backend:

```bash
# Google Sheets Configuration
GOOGLE_SHEETS_SPREADSHEET_ID=1rLSCtZkVU3WJ8qQz1l5Tv3L6aaAuqf_iKGaKaLMh2zQ
GOOGLE_SHEETS_CREDENTIALS_PATH=gsheet-onescan-service.json
GOOGLE_SHEETS_WORKSHEET_NAME=tracker
```

### 5. Share Google Sheets

1. Open your Google Sheets document
2. Click "Share" in the top right
3. Add your service account email (found in credentials.json) with "Editor" permissions

## Features

- **Automatic Sync**: Data is automatically synced to Google Sheets every 5 minutes
- **Persistent Storage**: Google Sheets data persists even when software data is cleared
- **Complete Data**: All tracker information including timestamps is synced
- **Error Handling**: Failed syncs are logged and retried

## Data Structure

The Google Sheets will contain the following columns:

1. Tracker Code
2. Tracking ID
3. Channel ID
4. Order ID
5. Sub Order ID
6. Courier
7. Channel Name
8. G-Code
9. EAN-Code
10. Product SKU
11. Channel Listing ID
12. Quantity
13. Amount
14. Payment Mode
15. Order Status
16. Buyer City
17. Buyer State
18. Buyer Pincode
19. Invoice Number
20. Last Updated
21. Sync Timestamp

## Troubleshooting

- **Authentication Errors**: Ensure credentials.json is properly configured
- **Permission Errors**: Make sure the service account has edit access to the spreadsheet
- **API Quotas**: Google Sheets API has rate limits, the 5-minute sync interval respects these limits 