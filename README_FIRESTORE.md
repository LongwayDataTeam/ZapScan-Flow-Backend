# Firestore Integration for ZapScan Flow Backend

This guide explains how to migrate from using `data.json` file storage to Google Firestore as a real database.

## 🚀 Benefits of Using Firestore

- **Real-time data**: Automatic synchronization across multiple clients
- **Scalability**: Handles large amounts of data efficiently
- **Reliability**: Google's infrastructure with 99.99% uptime
- **Security**: Built-in authentication and authorization
- **Backup**: Automatic backups and disaster recovery
- **Offline support**: Works even when internet is temporarily unavailable

## 📋 Prerequisites

1. **Google Cloud Project**: You need a Google Cloud project with Firestore enabled
2. **Firebase Admin SDK**: Service account credentials
3. **Python Dependencies**: Firebase Admin SDK for Python

## 🔧 Setup Instructions

### Step 1: Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project" or select an existing project
3. Enable Firestore Database:
   - Go to Firestore Database in the left sidebar
   - Click "Create database"
   - Choose "Start in test mode" for development
   - Select a location for your database

### Step 2: Generate Service Account Key

1. In Firebase Console, go to Project Settings (gear icon)
2. Click on "Service accounts" tab
3. Click "Generate new private key"
4. Download the JSON file and rename it to `firebase-service-account.json`
5. Place it in the `ZapScan-Flow-backend/` directory

### Step 3: Install Dependencies

```bash
cd ZapScan-Flow-backend
pip install -r minimal_requirements.txt
```

### Step 4: Configure Environment

1. Copy the environment template:
```bash
cp env.example .env
```

2. Edit `.env` file with your Firebase configuration:
```env
# Firebase Configuration
FIREBASE_SERVICE_ACCOUNT_PATH=firebase-service-account.json
FIREBASE_PROJECT_ID=your-firebase-project-id
USE_FIRESTORE=true
```

### Step 5: Migrate Existing Data (Optional)

If you have existing data in `data.json`, migrate it to Firestore:

```bash
python migrate_to_firestore.py
```

This script will:
- Create a backup of your `data.json` file
- Migrate all data to Firestore
- Verify the migration was successful

## 🏃‍♂️ Running the Application

### Option 1: Use the new Firestore backend

```bash
python firestore_backend.py
```

### Option 2: Use uvicorn directly

```bash
uvicorn firestore_backend:app --host 0.0.0.0 --port 8000 --reload
```

## 📊 Data Structure in Firestore

The application uses the following Firestore collections:

### Collections

1. **`scans`** - Scan records
   ```json
   {
     "id": "uuid",
     "tracker_code": "ASO21G39",
     "tracking_id": "ASO21G39",
     "scan_type": "label|packing|dispatch",
     "sku_details": {...},
     "timestamp": "2025-01-24T10:30:00",
     "status": "completed"
   }
   ```

2. **`tracker_status`** - Tracker completion status
   ```json
   {
     "ASO21G39": {
       "label": true,
       "packing": true,
       "dispatch": false
     }
   }
   ```

3. **`tracker_data`** - Detailed tracker information
   ```json
   {
     "ASO21G39": {
       "channel_id": "33618",
       "order_id": "17527751650573290M",
       "shipment_tracker": "ASO21G39",
       "courier": "JIO-Xpressbees",
       "channel_name": "Jiomart",
       "g_code": "ASO21G39",
       "ean_code": "ASO21G39",
       "product_sku_code": "LW-Dr-Mini-Black-PF-12-P1",
       "qty": 1,
       "amount": 1299.0,
       "payment_mode": "COD",
       "order_status": "Shipped",
       "buyer_city": "Birbhum",
       "buyer_state": "West Bengal",
       "buyer_pincode": "731101",
       "invoice_number": "S0719OYTGFA09143"
     }
   }
   ```

4. **`tracker_scan_count`** - Scan count statistics
   ```json
   {
     "ASO21G39": {
       "label": 15,
       "packing": 10,
       "dispatch": 7
     }
   }
   ```

5. **`tracker_scan_progress`** - Scan progress tracking
   ```json
   {
     "ASO21G39": {
       "label": {"scanned": 2, "total": 2},
       "packing": {"scanned": 1, "total": 2},
       "dispatch": {"scanned": 1, "total": 1}
     }
   }
   ```

6. **`system`** - System-wide data
   ```json
   {
     "uploaded_trackers": {
       "trackers": ["ASO21G39", "ASO21G40", ...]
     }
   }
   ```

## 🔄 API Endpoints

The Firestore backend provides the same API endpoints as the original backend:

### Tracker Management
- `POST /api/v1/trackers/upload/` - Upload tracker codes
- `POST /api/v1/trackers/upload-detailed/` - Upload detailed tracker data
- `GET /api/v1/trackers/uploaded/` - Get uploaded trackers
- `GET /api/v1/trackers/` - Get all trackers

### Scanning
- `POST /api/v1/scan/label/` - Process label scan
- `POST /api/v1/scan/packing/` - Process packing scan
- `POST /api/v1/scan/packing-dual/` - Process packing dual scan
- `POST /api/v1/scan/dispatch/` - Process dispatch scan

### Status & Statistics
- `GET /api/v1/tracker/{tracker_code}/status` - Get tracker status
- `GET /api/v1/tracker/{tracker_code}/packing-details` - Get packing details
- `GET /api/v1/tracker/{tracking_id}/count` - Get scan count
- `GET /api/v1/dashboard/stats` - Get dashboard statistics
- `GET /api/v1/tracking/stats` - Get tracking statistics

### Recent Scans
- `GET /api/v1/scan/recent` - Get recent scans
- `GET /api/v1/scan/recent/label` - Get recent label scans
- `GET /api/v1/scan/recent/packing` - Get recent packing scans
- `GET /api/v1/scan/recent/dispatch` - Get recent dispatch scans

### System Management
- `POST /api/v1/system/clear-data/` - Clear all data
- `POST /api/v1/system/migrate-from-json/` - Migrate from JSON

## 🔒 Security Considerations

1. **Service Account Key**: Keep your `firebase-service-account.json` secure and never commit it to version control
2. **Firestore Rules**: Set up proper Firestore security rules for production
3. **Environment Variables**: Use environment variables for sensitive configuration

### Example Firestore Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow read/write access to authenticated users
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

## 🐛 Troubleshooting

### Common Issues

1. **"Firestore not initialized" error**
   - Check that `firebase-service-account.json` exists and is valid
   - Verify your Firebase project ID is correct

2. **Permission denied errors**
   - Ensure your service account has proper permissions
   - Check Firestore security rules

3. **Connection timeout**
   - Verify your internet connection
   - Check if Firestore is enabled in your Firebase project

### Debug Mode

To enable debug logging, set the environment variable:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python firestore_backend.py
```

## 📈 Performance Tips

1. **Indexing**: Create composite indexes for complex queries
2. **Pagination**: Use the `limit` parameter for large datasets
3. **Caching**: Consider implementing client-side caching for frequently accessed data

## 🔄 Migration from data.json

If you're migrating from the existing `data.json` system:

1. **Backup your data**:
   ```bash
   cp data.json data_backup.json
   ```

2. **Run the migration script**:
   ```bash
   python migrate_to_firestore.py
   ```

3. **Verify the migration**:
   - Check that all data appears in Firestore console
   - Test the API endpoints with your frontend

4. **Switch to the new backend**:
   - Use `firestore_backend.py` instead of `simple_backend.py`
   - Update your frontend configuration if needed

## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to Firebase service account JSON | `firebase-service-account.json` |
| `FIREBASE_PROJECT_ID` | Firebase project ID | None |
| `USE_FIRESTORE` | Enable Firestore mode | `true` |
| `API_HOST` | API host address | `0.0.0.0` |
| `API_PORT` | API port number | `8000` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:3000` |

## 🤝 Support

If you encounter issues:

1. Check the Firebase Console for any errors
2. Verify your service account permissions
3. Test with a simple Firestore operation
4. Check the application logs for detailed error messages

## 📚 Additional Resources

- [Firebase Documentation](https://firebase.google.com/docs)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)
- [Firebase Admin SDK Python](https://firebase.google.com/docs/admin/setup#python)
- [FastAPI Documentation](https://fastapi.tiangolo.com/) 