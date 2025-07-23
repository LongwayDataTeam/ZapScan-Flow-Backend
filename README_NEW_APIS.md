# New Backend APIs for LabelScan Page

This document describes the new backend APIs that have been added to support the enhanced LabelScan page with real data integration.

## 🚀 New API Endpoints

### 1. Platform Statistics API
**Endpoint:** `GET /api/v1/scan/statistics/platform`

**Description:** Returns platform/courier statistics with scan counts for each courier.

**Response Format:**
```json
[
  {
    "courier": "Amazon DF",
    "total": 1028,
    "scanned": 660,
    "pending": 368
  },
  {
    "courier": "E-Delhivery", 
    "total": 30,
    "scanned": 0,
    "pending": 30
  }
]
```

### 2. Recent Scans API
**Endpoint:** `GET /api/v1/scan/recent`

**Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Records per page (default: 20, max: 100)

**Response Format:**
```json
{
  "results": [
    {
      "id": "1",
      "tracking_id": "TRK001234567",
      "platform": "Amazon DF",
      "last_scan": "Label",
      "scan_status": "Success",
      "distribution": "Single SKU",
      "scan_time": "2024-01-19 10:42:30",
      "amount": 1299.0,
      "buyer_city": "Mumbai",
      "courier": "Amazon DF"
    }
  ],
  "count": 150,
  "page": 1,
  "limit": 20,
  "total_pages": 8
}
```

## 📦 Setup Instructions

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python init_db.py
```

### 3. Populate Sample Data
```bash
python populate_sample_data.py
```

### 4. Start the Backend Server
```bash
python -m app.main
```

The server will start on `http://localhost:8000`

## 🧪 Testing the APIs

### 1. Test with Sample Data
```bash
python test_new_apis.py
```

### 2. Manual Testing with curl

**Platform Statistics:**
```bash
curl http://localhost:8000/api/v1/scan/statistics/platform
```

**Recent Scans (Page 1):**
```bash
curl "http://localhost:8000/api/v1/scan/recent?page=1&limit=10"
```

**Recent Scans (Page 2):**
```bash
curl "http://localhost:8000/api/v1/scan/recent?page=2&limit=10"
```

### 3. API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation.

## 📊 Sample Data Structure

The sample data includes:

- **6 Couriers:** Amazon DF, E-Delhivery, E-Large, BlueDart, DTDC, FedEx
- **50 Orders** with varying scan statuses
- **Scan Checkpoints** for Label, Packing, and Dispatch stages
- **Realistic Data** with amounts, cities, and distribution types

## 🔧 API Features

### Platform Statistics
- ✅ Groups orders by courier
- ✅ Calculates total, scanned, and pending counts
- ✅ Sorts by total count (descending)
- ✅ Handles missing courier data gracefully

### Recent Scans
- ✅ Pagination support with configurable limits
- ✅ Joins with order data for complete information
- ✅ Formats scan times and statuses
- ✅ Determines distribution type (Single/Multi SKU)
- ✅ Sorts by scan time (newest first)

### Error Handling
- ✅ Graceful error responses
- ✅ Input validation
- ✅ Database connection error handling
- ✅ Missing data handling

## 🎯 Frontend Integration

The frontend LabelScan page now:

1. **Fetches real data** from these APIs
2. **Shows loading states** while data is being retrieved
3. **Handles errors gracefully** with fallback to mock data
4. **Refreshes data** after successful scans
5. **Supports pagination** for large datasets

## 🐛 Troubleshooting

### Common Issues:

1. **Database Connection Error:**
   - Ensure database is initialized: `python init_db.py`
   - Check database configuration in `app/core/config.py`

2. **No Data Showing:**
   - Run sample data population: `python populate_sample_data.py`
   - Check database tables exist

3. **API 500 Errors:**
   - Check backend logs for detailed error messages
   - Verify all required models are imported

4. **CORS Issues:**
   - Ensure frontend is running on allowed origins
   - Check CORS configuration in `app/main.py`

## 📈 Performance Notes

- **Platform Statistics:** Cached at application level for better performance
- **Recent Scans:** Uses database indexing for fast pagination
- **Large Datasets:** Pagination prevents memory issues
- **Real-time Updates:** Data refreshes after each scan operation

## 🔄 API Updates

The APIs automatically update when:
- New scans are processed
- Orders are added/modified
- Scan statuses change

This ensures the frontend always shows current data without manual refresh. 