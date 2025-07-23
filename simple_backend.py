#!/usr/bin/env python3
"""
Minimal FastAPI backend for Fulfillment Tracking System
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from datetime import datetime

app = FastAPI(title="Fulfillment Tracking API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class ScanRequest(BaseModel):
    tracker_code: str
    scan_type: str  # "label", "packing", "dispatch"

class TrackerUpload(BaseModel):
    tracker_codes: List[str]

class TrackerData(BaseModel):
    channel_id: Optional[str] = None
    order_id: Optional[str] = None
    sub_order_id: Optional[str] = None
    shipment_tracker: str
    courier: Optional[str] = None
    channel_name: Optional[str] = None
    g_code: Optional[str] = None
    ean_code: Optional[str] = None
    product_sku_code: Optional[str] = None
    channel_listing_id: Optional[str] = None
    qty: Optional[int] = None
    amount: Optional[float] = None
    payment_mode: Optional[str] = None
    order_status: Optional[str] = None
    buyer_city: Optional[str] = None
    buyer_state: Optional[str] = None
    buyer_pincode: Optional[str] = None
    invoice_number: Optional[str] = None

class TrackerDataUpload(BaseModel):
    trackers: List[TrackerData]

# Global data storage
scans_db = []
tracker_status = {}
uploaded_trackers = []
tracker_data = {}
tracker_scan_count = {}
tracker_scan_progress = {}

def load_data():
    """Load data from JSON file"""
    global scans_db, tracker_status, uploaded_trackers, tracker_data, tracker_scan_count, tracker_scan_progress
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
            scans_db = data.get('scans', [])
            tracker_status = data.get('tracker_status', {})
            uploaded_trackers = data.get('uploaded_trackers', [])
            tracker_data = data.get('tracker_data', {})
            tracker_scan_count = data.get('tracker_scan_count', {})
            tracker_scan_progress = data.get('tracker_scan_progress', {})
    except FileNotFoundError:
        # Initialize with empty data if file doesn't exist
        pass

def save_data():
    """Save data to JSON file"""
    data = {
        'scans': scans_db,
        'tracker_status': tracker_status,
        'uploaded_trackers': uploaded_trackers,
        'tracker_data': tracker_data,
        'tracker_scan_count': tracker_scan_count,
        'tracker_scan_progress': tracker_scan_progress
    }
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=2)

def get_trackers_by_tracking_id(tracking_id: str):
    """Get all trackers that belong to the same tracking ID (case-insensitive)"""
    trackers = []
    
    # Convert tracking_id to uppercase for case-insensitive matching
    tracking_id_upper = tracking_id.upper()
    
    # Find all trackers with the exact tracking_id (case-insensitive)
    for tracker_code, data in tracker_data.items():
        # Convert stored shipment_tracker to uppercase for comparison
        stored_tracker = data.get('shipment_tracker', '').upper()
        if stored_tracker == tracking_id_upper:
            trackers.append({
                'tracker_code': tracker_code,
                'channel_id': data.get('channel_id'),
                'g_code': data.get('g_code'),
                'ean_code': data.get('ean_code'),
                'product_sku_code': data.get('product_sku_code'),
                'qty': data.get('qty', 1)
            })
    
    # Sort by channel_id for consistent ordering
    trackers.sort(key=lambda x: x.get('channel_id', ''))
    return trackers

def scan_all_trackers_for_tracking_id(tracking_id: str, scan_type: str):
    """Scan all trackers for a given tracking ID at once"""
    trackers = get_trackers_by_tracking_id(tracking_id)
    if not trackers:
        return None
    
    scanned_trackers = []
    scan_records = []
    
    for tracker in trackers:
        tracker_code = tracker['tracker_code']
        
        # Check if this tracker is already scanned for this scan type
        if tracker_code in tracker_status and tracker_status[tracker_code].get(scan_type, False):
            continue  # Skip already scanned trackers
        
        # Create scan record
        scan_record = {
            "id": str(len(scans_db) + 1),
            "tracker_code": tracker_code,
            "tracking_id": tracking_id,
            "scan_type": scan_type,
            "sku_details": {
                "g_code": tracker['g_code'],
                "ean_code": tracker['ean_code'],
                "product_sku_code": tracker['product_sku_code'],
                "channel_id": tracker['channel_id']
            },
            "timestamp": datetime.now().isoformat(),
            "status": "completed"
        }
        scans_db.append(scan_record)
        scan_records.append(scan_record)
        
        # Update tracker status for this specific SKU
        if tracker_code not in tracker_status:
            tracker_status[tracker_code] = {"label": False, "packing": False, "dispatch": False}
        tracker_status[tracker_code][scan_type] = True
        
        scanned_trackers.append(tracker)
    
    # Update scan count and progress
    if tracking_id not in tracker_scan_count:
        tracker_scan_count[tracking_id] = {}
    tracker_scan_count[tracking_id][scan_type] = tracker_scan_count[tracking_id].get(scan_type, 0) + len(scanned_trackers)
    
    # Update progress for all scanned trackers
    for _ in range(len(scanned_trackers)):
        update_scan_progress(tracking_id, scan_type)
    
    # Get updated progress
    progress = get_scan_progress(tracking_id, scan_type)
    
    return {
        "scanned_trackers": scanned_trackers,
        "scan_records": scan_records,
        "progress": progress,
        "total_scanned": len(scanned_trackers)
    }

def get_next_sku_to_scan(tracking_id: str, scan_type: str):
    """Get the next SKU to scan for a tracking ID"""
    trackers = get_trackers_by_tracking_id(tracking_id)
    if not trackers:
        return None
    
    # Sort trackers by channel_id for consistent ordering
    trackers.sort(key=lambda x: x.get('channel_id', ''))
    
    # Find the next un-scanned tracker for this scan type
    for tracker in trackers:
        tracker_code = tracker['tracker_code']
        
        # Check if this tracker is already scanned for this scan type
        if tracker_code in tracker_status:
            if not tracker_status[tracker_code].get(scan_type, False):
                # This tracker hasn't been scanned for this scan type yet
                return tracker
        else:
            # Tracker status doesn't exist, so it hasn't been scanned
            return tracker
    
    # All trackers have been scanned for this scan type
    return None

def update_scan_progress(tracking_id: str, scan_type: str):
    """Update scan progress for a tracking ID"""
    if tracking_id not in tracker_scan_progress:
        tracker_scan_progress[tracking_id] = {}
    
    if scan_type not in tracker_scan_progress[tracking_id]:
        tracker_scan_progress[tracking_id][scan_type] = {"scanned": 0, "total": 0}
    
    # Get all trackers for this tracking ID
    trackers = get_trackers_by_tracking_id(tracking_id)
    total = len(trackers)
    
    # Count scanned trackers
    scanned = 0
    for tracker in trackers:
        tracker_code = tracker['tracker_code']
        if tracker_code in tracker_status and tracker_status[tracker_code].get(scan_type, False):
            scanned += 1
    
    tracker_scan_progress[tracking_id][scan_type] = {"scanned": scanned, "total": total}

def get_scan_progress(tracking_id: str, scan_type: str) -> dict:
    """Get scan progress for a tracking ID"""
    if tracking_id not in tracker_scan_progress:
        tracker_scan_progress[tracking_id] = {}
    
    if scan_type not in tracker_scan_progress[tracking_id]:
        # Initialize progress
        trackers = get_trackers_by_tracking_id(tracking_id)
        total = len(trackers)
        scanned = 0
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            if tracker_code in tracker_status and tracker_status[tracker_code].get(scan_type, False):
                scanned += 1
        tracker_scan_progress[tracking_id][scan_type] = {"scanned": scanned, "total": total}
    
    return tracker_scan_progress[tracking_id][scan_type]

def generate_unique_tracker_key(base_tracker_code: str, existing_keys: list) -> str:
    """Generate a unique tracker key for multi-SKU orders"""
    if base_tracker_code not in existing_keys:
        return base_tracker_code
    
    # Find the next available suffix
    counter = 1
    while f"{base_tracker_code}_{counter}" in existing_keys:
        counter += 1
    
    return f"{base_tracker_code}_{counter}"

def fix_existing_data_structure():
    """Fix existing data structure to have proper _1, _2, _3 suffixes"""
    global tracker_status, tracker_data, uploaded_trackers
    
    print("Fixing data structure...")
    
    # Find all tracking IDs that have suffixes
    tracking_groups = {}
    for key in tracker_status.keys():
        if '_' in key:
            base_id = key.split('_')[0]
            suffix = key.split('_')[1]
            if base_id not in tracking_groups:
                tracking_groups[base_id] = []
            tracking_groups[base_id].append((key, suffix))
    
    # Create new data structures
    new_tracker_status = {}
    new_tracker_data = {}
    new_uploaded_trackers = []
    
    # Process each tracking group
    for base_id, items in tracking_groups.items():
        # Sort by suffix number
        items.sort(key=lambda x: int(x[1]) if x[1].isdigit() else 999)
        
        # Create new keys starting from _1
        for i, (old_key, old_suffix) in enumerate(items, 1):
            new_key = f"{base_id}_{i}"
            
            print(f"  {old_key} -> {new_key}")
            
            # Update tracker_status
            if old_key in tracker_status:
                new_tracker_status[new_key] = tracker_status[old_key]
            
            # Update tracker_data
            if old_key in tracker_data:
                new_tracker_data[new_key] = tracker_data[old_key]
            
            # Update uploaded_trackers
            if old_key in uploaded_trackers:
                new_uploaded_trackers.append(new_key)
    
    # Add keys that don't have suffixes
    for key in tracker_status.keys():
        if '_' not in key:
            new_tracker_status[key] = tracker_status[key]
            if key in tracker_data:
                new_tracker_data[key] = tracker_data[key]
            if key in uploaded_trackers:
                new_uploaded_trackers.append(key)
    
    # Update global variables
    tracker_status = new_tracker_status
    tracker_data = new_tracker_data
    uploaded_trackers = new_uploaded_trackers
    
    save_data()
    print("Data structure fixed successfully!")

# Load data on startup
load_data()

# Fix data structure on startup if needed
def startup_fix():
    """Fix data structure on startup"""
    try:
        # Check if there are any keys with _2, _3, _4 but no _1
        needs_fixing = False
        for key in tracker_status.keys():
            if '_' in key:
                base_id = key.split('_')[0]
                suffix = key.split('_')[1]
                if suffix.isdigit() and int(suffix) > 1:
                    # Check if _1 exists
                    if f"{base_id}_1" not in tracker_status:
                        needs_fixing = True
                        break
        
        if needs_fixing:
            print("Detected inconsistent data structure. Fixing...")
            fix_existing_data_structure()
        else:
            print("Data structure is consistent.")
    except Exception as e:
        print(f"Error during startup fix: {e}")

# Run startup fix
startup_fix()

# Basic endpoints
@app.get("/")
async def root():
    return {"message": "Fulfillment Tracking API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Tracker upload endpoints
@app.post("/api/v1/trackers/upload/")
async def upload_trackers(tracker_upload: TrackerUpload):
    """Upload tracker codes"""
    global uploaded_trackers
    
    # Add all trackers to the list (including duplicates)
    for tracker_code in tracker_upload.tracker_codes:
        uploaded_trackers.append(tracker_code)
        # Initialize tracker status if not exists
        if tracker_code not in tracker_status:
            tracker_status[tracker_code] = {"label": False, "packing": False, "dispatch": False}
    
    save_data()
    
    return {
        "message": f"Successfully uploaded {len(tracker_upload.tracker_codes)} trackers",
        "total_trackers": len(uploaded_trackers),
        "uploaded_trackers": tracker_upload.tracker_codes
    }

@app.post("/api/v1/trackers/upload-detailed/")
async def upload_detailed_trackers(tracker_data_upload: TrackerDataUpload):
    """Upload detailed tracker data"""
    global uploaded_trackers, tracker_data
    
    for i, tracker in enumerate(tracker_data_upload.trackers):
        # Create a unique tracker code that preserves the original data
        base_tracker_code = tracker.shipment_tracker
        
        # Check if this shipment_tracker already exists
        existing_keys = [k for k, v in tracker_data.items() if v.get('shipment_tracker') == base_tracker_code]
        
        # Generate unique tracker key using helper function
        tracker_code = generate_unique_tracker_key(base_tracker_code, existing_keys)
        
        # Add to uploaded trackers list
        uploaded_trackers.append(tracker_code)
        
        # Store detailed tracker data with unique key
        tracker_data[tracker_code] = {
            "channel_id": tracker.channel_id,
            "order_id": tracker.order_id,
            "sub_order_id": tracker.sub_order_id,
            "shipment_tracker": tracker.shipment_tracker,  # Keep original shipment_tracker
            "courier": tracker.courier,
            "channel_name": tracker.channel_name,
            "g_code": tracker.g_code,
            "ean_code": tracker.ean_code,
            "product_sku_code": tracker.product_sku_code,
            "qty": tracker.qty,
            "amount": tracker.amount,
            "payment_mode": tracker.payment_mode,
            "order_status": tracker.order_status,
            "buyer_city": tracker.buyer_city,
            "buyer_state": tracker.buyer_state,
            "buyer_pincode": tracker.buyer_pincode,
            "invoice_number": tracker.invoice_number
        }
        
        # Initialize tracker status if not exists
        if tracker_code not in tracker_status:
            tracker_status[tracker_code] = {"label": False, "packing": False, "dispatch": False}
    
    save_data()
    
    return {
        "message": f"Successfully uploaded {len(tracker_data_upload.trackers)} tracker entries",
        "uploaded_count": len(tracker_data_upload.trackers),
        "total_trackers": len(uploaded_trackers)
    }

@app.get("/api/v1/trackers/uploaded/")
async def get_uploaded_trackers():
    """Get all uploaded trackers"""
    return {
        "uploaded_trackers": uploaded_trackers,
        "total_count": len(uploaded_trackers)
    }

@app.get("/api/v1/tracker/{tracker_code}/details")
async def get_tracker_details(tracker_code: str):
    """Get detailed information for a specific tracker"""
    if tracker_code not in uploaded_trackers:
        raise HTTPException(status_code=404, detail="Tracker not found")
    
    details = tracker_data.get(tracker_code, {})
    status = tracker_status.get(tracker_code, {"label": False, "packing": False, "dispatch": False})
    
    return {
        "tracker_code": tracker_code,
        "details": details,
        "status": status
    }

# Scan endpoints
@app.post("/api/v1/scan/label/")
async def process_label_scan(scan_request: ScanRequest):
    """Process label scan - scan all trackers for tracking ID at once"""
    tracking_id = scan_request.tracker_code
    
    # Check if tracking ID exists in tracker data
    trackers = get_trackers_by_tracking_id(tracking_id)
    if not trackers:
        raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
    
    # Scan all trackers for this tracking ID at once
    scan_result = scan_all_trackers_for_tracking_id(tracking_id, "label")
    if not scan_result or scan_result["total_scanned"] == 0:
        raise HTTPException(status_code=400, detail="All SKUs for this tracking ID have been scanned")
    
    save_data()
    
    # Get the first scanned SKU for response (for backward compatibility)
    first_scanned = scan_result["scanned_trackers"][0] if scan_result["scanned_trackers"] else None
    
    return {
        "message": f"Label scan completed for {scan_result['total_scanned']} SKU(s)",
        "scan": scan_result["scan_records"][0] if scan_result["scan_records"] else None,
        "sku_scanned": {
            "g_code": first_scanned['g_code'] if first_scanned else None,
            "ean_code": first_scanned['ean_code'] if first_scanned else None,
            "product_sku_code": first_scanned['product_sku_code'] if first_scanned else None,
            "channel_id": first_scanned['channel_id'] if first_scanned else None
        },
        "progress": scan_result["progress"],
        "total_scanned": scan_result["total_scanned"],
        "next_step": "packing"
    }

@app.post("/api/v1/scan/packing/")
async def process_packing_scan(scan_request: ScanRequest):
    """Process packing scan with Multi-SKU support"""
    tracking_id = scan_request.tracker_code
    
    # Check if tracking ID exists in tracker data
    trackers = get_trackers_by_tracking_id(tracking_id)
    if not trackers:
        raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
    
    # Get next SKU to scan
    next_sku = get_next_sku_to_scan(tracking_id, "packing")
    if not next_sku:
        raise HTTPException(status_code=400, detail="All SKUs for this tracking ID have been scanned")
    
    # Check if this specific tracker is already scanned
    tracker_code = next_sku['tracker_code']
    if tracker_code in tracker_status and tracker_status[tracker_code].get("packing", False):
        raise HTTPException(status_code=400, detail="This SKU has already been scanned")
    
    # Check if label scan is completed for this SKU
    if tracker_code not in tracker_status or not tracker_status[tracker_code].get("label", False):
        raise HTTPException(status_code=400, detail="Label scan must be completed before packing scan")
    
    # Create scan record
    scan_record = {
        "id": str(len(scans_db) + 1),
        "tracker_code": tracker_code,
        "tracking_id": tracking_id,
        "scan_type": "packing",
        "sku_details": {
            "g_code": next_sku['g_code'],
            "ean_code": next_sku['ean_code'],
            "product_sku_code": next_sku['product_sku_code'],
            "channel_id": next_sku['channel_id']
        },
        "timestamp": datetime.now().isoformat(),
        "status": "completed"
    }
    scans_db.append(scan_record)
    
    # Update tracker status for this specific SKU
    tracker_status[tracker_code]["packing"] = True
    
    # Update scan count and progress
    if tracking_id not in tracker_scan_count:
        tracker_scan_count[tracking_id] = {}
    tracker_scan_count[tracking_id]["packing"] = tracker_scan_count[tracking_id].get("packing", 0) + 1
    
    update_scan_progress(tracking_id, "packing")
    
    # Get updated progress
    progress = get_scan_progress(tracking_id, "packing")
    
    save_data()
    
    return {
        "message": f"Packing scan completed for SKU: {next_sku['product_sku_code']}",
        "scan": scan_record,
        "sku_scanned": {
            "g_code": next_sku['g_code'],
            "ean_code": next_sku['ean_code'],
            "product_sku_code": next_sku['product_sku_code'],
            "channel_id": next_sku['channel_id']
        },
        "progress": progress,
        "next_step": "dispatch" if progress["scanned"] < progress["total"] else "dispatch"
    }

class PackingDualScanRequest(BaseModel):
    tracker_code: str
    product_code: str  # G-Code or EAN-Code

@app.post("/api/v1/scan/packing-dual/")
async def process_packing_dual_scan(scan_request: PackingDualScanRequest):
    """Process packing dual scan (tracker + product code)"""
    tracking_id = scan_request.tracker_code
    product_code = scan_request.product_code
    
    print(f"DEBUG: Packing dual scan requested for tracking_id: {tracking_id}, product_code: {product_code}")
    
    # Get trackers for this tracking ID
    trackers = get_trackers_by_tracking_id(tracking_id)
    if not trackers:
        print(f"DEBUG: No trackers found for {tracking_id}")
        raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
    
    print(f"DEBUG: Found {len(trackers)} trackers for {tracking_id}")
    
    # Get the next SKU to scan for packing
    next_sku = get_next_sku_to_scan(tracking_id, "packing")
    if not next_sku:
        print(f"DEBUG: No next SKU found for {tracking_id}")
        raise HTTPException(status_code=400, detail="All SKUs for this tracking ID have been scanned")
    
    tracker_code = next_sku['tracker_code']
    print(f"DEBUG: Next SKU tracker_code: {tracker_code}")
    
    # Check if already scanned
    if tracker_code in tracker_status and tracker_status[tracker_code].get("packing", False):
        print(f"DEBUG: Tracker {tracker_code} already scanned for packing")
        raise HTTPException(status_code=400, detail="Packing scan already completed for this SKU")
    
    # Validate product code (check if it matches the tracker's product)
    g_code = next_sku['g_code']
    ean_code = next_sku['ean_code']
    
    print(f"DEBUG: Expected G-Code: {g_code}, EAN-Code: {ean_code}")
    print(f"DEBUG: Scanned product code: {product_code}")
    
    if product_code not in [g_code, ean_code]:
        print(f"DEBUG: Product code mismatch")
        raise HTTPException(
            status_code=400, 
            detail=f"Product code {product_code} does not match tracker's G-Code ({g_code}) or EAN-Code ({ean_code})"
        )
    
    print(f"DEBUG: Product code validated successfully")
    
    scan_record = {
        "id": str(len(scans_db) + 1),
        "tracker_code": tracker_code,
        "tracking_id": tracking_id,
        "scan_type": "packing_dual",
        "product_code": product_code,
        "timestamp": datetime.now().isoformat(),
        "status": "completed"
    }
    scans_db.append(scan_record)
    
    # Update tracker status
    if tracker_code not in tracker_status:
        tracker_status[tracker_code] = {"label": False, "packing": False, "dispatch": False}
    tracker_status[tracker_code]["packing"] = True
    
    # Update scan progress
    update_scan_progress(tracking_id, "packing")
    
    save_data()
    
    print(f"DEBUG: Packing dual scan completed successfully")
    
    return {
        "message": "Packing dual scan processed successfully",
        "scan": scan_record,
        "next_step": "dispatch",
        "matched_product": {
            "g_code": g_code,
            "ean_code": ean_code,
            "scanned_code": product_code
        }
    }

@app.post("/api/v1/scan/dispatch/")
async def process_dispatch_scan(scan_request: ScanRequest):
    """Process dispatch scan - scan all trackers for tracking ID at once"""
    tracking_id = scan_request.tracker_code
    
    # Check if tracking ID exists in tracker data
    trackers = get_trackers_by_tracking_id(tracking_id)
    if not trackers:
        raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
    
    # Check if all previous scans are completed for all trackers
    for tracker in trackers:
        tracker_code = tracker['tracker_code']
        if tracker_code not in tracker_status:
            raise HTTPException(status_code=400, detail="Label and packing scans must be completed before dispatch scan")
        
        if not tracker_status[tracker_code].get("label", False):
            raise HTTPException(status_code=400, detail="Label scan must be completed before dispatch scan")
        
        if not tracker_status[tracker_code].get("packing", False):
            raise HTTPException(status_code=400, detail="Packing scan must be completed before dispatch scan")
    
    # Scan all trackers for this tracking ID at once
    scan_result = scan_all_trackers_for_tracking_id(tracking_id, "dispatch")
    if not scan_result or scan_result["total_scanned"] == 0:
        raise HTTPException(status_code=400, detail="All SKUs for this tracking ID have been scanned")
    
    save_data()
    
    # Get the first scanned SKU for response (for backward compatibility)
    first_scanned = scan_result["scanned_trackers"][0] if scan_result["scanned_trackers"] else None
    
    return {
        "message": f"Dispatch scan completed for {scan_result['total_scanned']} SKU(s)",
        "scan": scan_result["scan_records"][0] if scan_result["scan_records"] else None,
        "sku_scanned": {
            "g_code": first_scanned['g_code'] if first_scanned else None,
            "ean_code": first_scanned['ean_code'] if first_scanned else None,
            "product_sku_code": first_scanned['product_sku_code'] if first_scanned else None,
            "channel_id": first_scanned['channel_id'] if first_scanned else None
        },
        "progress": scan_result["progress"],
        "total_scanned": scan_result["total_scanned"],
        "next_step": "completed"
    }

# Tracker status endpoints
@app.get("/api/v1/tracker/{tracker_code}/status")
async def get_tracker_status(tracker_code: str):
    """Get status of a specific tracker"""
    if tracker_code not in uploaded_trackers:
        return {
            "tracker_code": tracker_code,
            "status": "not_uploaded",
            "label": False,
            "packing": False,
            "dispatch": False,
            "next_available_scan": "not_available"
        }
    
    if tracker_code not in tracker_status:
        return {
            "tracker_code": tracker_code,
            "status": "not_started",
            "label": False,
            "packing": False,
            "dispatch": False,
            "next_available_scan": "label"
        }
    
    status = tracker_status[tracker_code]
    next_scan = "completed"
    if not status.get("label", False):
        next_scan = "label"
    elif not status.get("packing", False):
        next_scan = "packing"
    elif not status.get("dispatch", False):
        next_scan = "dispatch"
    
    return {
        "tracker_code": tracker_code,
        "status": "completed" if status.get("dispatch", False) else "in_progress",
        "label": status.get("label", False),
        "packing": status.get("packing", False),
        "dispatch": status.get("dispatch", False),
        "next_available_scan": next_scan
    }

@app.get("/api/v1/tracker/{tracking_id}/count")
async def get_tracker_scan_count(tracking_id: str):
    """Get scan count and progress for a tracking ID"""
    # Check if tracking ID exists in tracker data
    trackers = get_trackers_by_tracking_id(tracking_id)
    if not trackers:
        raise HTTPException(status_code=404, detail="Tracking ID not found")
    
    # Get progress for each scan type
    label_progress = get_scan_progress(tracking_id, "label")
    packing_progress = get_scan_progress(tracking_id, "packing")
    dispatch_progress = get_scan_progress(tracking_id, "dispatch")
    
    # Get scan counts
    label_count = tracker_scan_count.get(tracking_id, {}).get("label", 0)
    packing_count = tracker_scan_count.get(tracking_id, {}).get("packing", 0)
    dispatch_count = tracker_scan_count.get(tracking_id, {}).get("dispatch", 0)
    
    return {
        "tracking_id": tracking_id,
        "total_skus": len(trackers),
        "label": {
            "scanned": label_count,
            "total": len(trackers),
            "progress": label_progress
        },
        "packing": {
            "scanned": packing_count,
            "total": len(trackers),
            "progress": packing_progress
        },
        "dispatch": {
            "scanned": dispatch_count,
            "total": len(trackers),
            "progress": dispatch_progress
        },
        "skus": trackers
    }

@app.get("/api/v1/trackers/")
async def get_all_trackers():
    """Get all trackers and their status"""
    trackers = []
    for code in uploaded_trackers:
        if code in tracker_status:
            status = tracker_status[code]
            next_scan = "label" if not status.get("label", False) else \
                       "packing" if not status.get("packing", False) else \
                       "dispatch" if not status.get("dispatch", False) else "completed"
            
            # Get the original tracking ID from tracker data
            tracker_info = tracker_data.get(code, {})
            original_tracking_id = tracker_info.get('shipment_tracker', code)
            
            trackers.append({
                "tracker_code": code,
                "original_tracking_id": original_tracking_id,
                "status": status,
                "next_available_scan": next_scan,
                "details": tracker_data.get(code, {})
            })
        else:
            # Get the original tracking ID from tracker data
            tracker_info = tracker_data.get(code, {})
            original_tracking_id = tracker_info.get('shipment_tracker', code)
            
            trackers.append({
                "tracker_code": code,
                "original_tracking_id": original_tracking_id,
                "status": {"label": False, "packing": False, "dispatch": False},
                "next_available_scan": "label",
                "details": tracker_data.get(code, {})
            })
    
    return {"trackers": trackers}

# Comprehensive tracking statistics
@app.get("/api/v1/tracking/stats")
async def get_tracking_statistics():
    """Get comprehensive tracking statistics"""
    total_uploaded = len(uploaded_trackers)
    
    if total_uploaded == 0:
        return {
            "total_uploaded": 0,
            "label_scanned": 0,
            "packing_scanned": 0,
            "dispatch_scanned": 0,
            "completed": 0,
            "label_percentage": 0,
            "packing_percentage": 0,
            "dispatch_percentage": 0,
            "completion_percentage": 0
        }
    
    label_scanned = sum(1 for code in uploaded_trackers if code in tracker_status and tracker_status[code].get("label", False))
    packing_scanned = sum(1 for code in uploaded_trackers if code in tracker_status and tracker_status[code].get("packing", False))
    dispatch_scanned = sum(1 for code in uploaded_trackers if code in tracker_status and tracker_status[code].get("dispatch", False))
    completed = sum(1 for code in uploaded_trackers if code in tracker_status and tracker_status[code].get("dispatch", False))
    
    return {
        "total_uploaded": total_uploaded,
        "label_scanned": label_scanned,
        "packing_scanned": packing_scanned,
        "dispatch_scanned": dispatch_scanned,
        "completed": completed,
        "label_percentage": round((label_scanned / total_uploaded) * 100, 1),
        "packing_percentage": round((packing_scanned / total_uploaded) * 100, 1),
        "dispatch_percentage": round((dispatch_scanned / total_uploaded) * 100, 1),
        "completion_percentage": round((completed / total_uploaded) * 100, 1)
    }

@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    total_uploaded = len(uploaded_trackers)
    
    if total_uploaded == 0:
        return {
            "total_trackers": 0,
            "completed_trackers": 0,
            "in_progress_trackers": 0,
            "pending_trackers": 0,
            "completion_rate": 0
        }
    
    completed = sum(1 for code in uploaded_trackers if code in tracker_status and tracker_status[code].get("dispatch", False))
    in_progress = sum(1 for code in uploaded_trackers if code in tracker_status and (tracker_status[code].get("label", False) or tracker_status[code].get("packing", False)) and not tracker_status[code].get("dispatch", False))
    pending = total_uploaded - completed - in_progress
    
    return {
        "total_trackers": total_uploaded,
        "completed_trackers": completed,
        "in_progress_trackers": in_progress,
        "pending_trackers": pending,
        "completion_rate": round((completed / total_uploaded) * 100, 1)
    }

@app.post("/api/v1/system/clear-data/")
async def clear_all_data():
    """Clear all data"""
    global scans_db, tracker_status, uploaded_trackers, tracker_data
    
    scans_db = []
    tracker_status = {}
    uploaded_trackers = []
    tracker_data = {}
    
    save_data()
    
    return {"message": "All data cleared successfully"}

# New API endpoints for LabelScan page
@app.get("/api/v1/scan/statistics/platform")
async def get_platform_statistics(scan_type: str = None):
    """Get platform/courier statistics with scan counts including Multi-SKU and Single-SKU breakdown"""
    try:
        # Group trackers by courier and calculate statistics
        courier_stats = {}
        
        # Group trackers by tracking ID to identify Multi-SKU orders
        tracking_id_groups = {}
        for tracker_code in uploaded_trackers:
            tracker_info = tracker_data.get(tracker_code, {})
            tracking_id = tracker_info.get('shipment_tracker', '')
            if tracking_id:
                if tracking_id not in tracking_id_groups:
                    tracking_id_groups[tracking_id] = []
                tracking_id_groups[tracking_id].append(tracker_code)
        
        for tracker_code in uploaded_trackers:
            tracker_info = tracker_data.get(tracker_code, {})
            courier = tracker_info.get('courier', 'Unknown')
            tracking_id = tracker_info.get('shipment_tracker', '')
            
            if courier not in courier_stats:
                courier_stats[courier] = {
                    "courier": courier,
                    "total": 0,
                    "scanned": 0,
                    "pending": 0,
                    "multi_sku_scanned": 0,
                    "single_sku_scanned": 0,
                    "multi_sku_pending": 0,
                    "single_sku_pending": 0
                }
            
            courier_stats[courier]["total"] += 1
            
            # Check if tracker has been scanned based on scan_type parameter
            tracker_status_info = tracker_status.get(tracker_code, {})
            
            if scan_type:
                # Filter by specific scan type
                if scan_type == "label":
                    has_scans = tracker_status_info.get("label", False)
                elif scan_type == "packing":
                    has_scans = tracker_status_info.get("packing", False)
                elif scan_type == "dispatch":
                    has_scans = tracker_status_info.get("dispatch", False)
                else:
                    has_scans = any(tracker_status_info.values())
            else:
                # Default behavior - check if tracker has been scanned at any checkpoint
                has_scans = any(tracker_status_info.values())
            
            # Determine if this is part of a Multi-SKU order
            is_multi_sku = len(tracking_id_groups.get(tracking_id, [])) > 1
            
            if has_scans:
                courier_stats[courier]["scanned"] += 1
                if is_multi_sku:
                    courier_stats[courier]["multi_sku_scanned"] += 1
                else:
                    courier_stats[courier]["single_sku_scanned"] += 1
            else:
                courier_stats[courier]["pending"] += 1
                if is_multi_sku:
                    courier_stats[courier]["multi_sku_pending"] += 1
                else:
                    courier_stats[courier]["single_sku_pending"] += 1
        
        # Convert to list and sort by total count
        result = list(courier_stats.values())
        result.sort(key=lambda x: x["total"], reverse=True)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching platform statistics: {str(e)}")

@app.get("/api/v1/scan/recent")
async def get_recent_scans(page: int = 1, limit: int = 20):
    """Get recent scans with pagination"""
    try:
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get recent scans with tracker details
        recent_scans = []
        for scan in scans_db[offset:offset + limit]:
            tracker_code = scan.get('tracker_code', '')
            tracker_info = tracker_data.get(tracker_code, {})
            
            # Determine last scan type
            last_scan = scan.get('scan_type', 'label').capitalize()
            
            # Determine scan status
            scan_status = "Success" if scan.get('status', '') == 'completed' else "Error"
            
            # Determine distribution type (simplified - assume single SKU for now)
            distribution = "Single SKU"
            
            # Format scan time
            scan_time = scan.get('timestamp', '')
            if scan_time:
                try:
                    dt = datetime.fromisoformat(scan_time.replace('Z', '+00:00'))
                    scan_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    scan_time = scan_time
            
            recent_scans.append({
                "id": str(scan.get('id', '')),
                "tracking_id": tracker_info.get('shipment_tracker', tracker_code),
                "platform": tracker_info.get('channel_name', 'Unknown'),
                "last_scan": last_scan,
                "scan_status": scan_status,
                "distribution": distribution,
                "scan_time": scan_time,
                "amount": tracker_info.get('amount', 0),
                "buyer_city": tracker_info.get('buyer_city', 'Unknown'),
                "courier": tracker_info.get('courier', 'Unknown')
            })
        
        return {
            "results": recent_scans,
            "count": len(scans_db),
            "page": page,
            "limit": limit,
            "total_pages": (len(scans_db) + limit - 1) // limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent scans: {str(e)}")

@app.get("/api/v1/scan/recent/label")
async def get_recent_label_scans(page: int = 1, limit: int = 20):
    """Get recent label scans with pagination"""
    try:
        # Filter scans for label type only
        label_scans = [scan for scan in scans_db if scan.get('scan_type') == 'label']
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get recent label scans with tracker details
        recent_scans = []
        for scan in label_scans[offset:offset + limit]:
            tracker_code = scan.get('tracker_code', '')
            tracker_info = tracker_data.get(tracker_code, {})
            
            # Determine scan status
            scan_status = "Success" if scan.get('status', '') == 'completed' else "Error"
            
            # Determine distribution type
            tracking_id = tracker_info.get('shipment_tracker', '')
            trackers_with_same_id = [t for t in uploaded_trackers if tracker_data.get(t, {}).get('shipment_tracker') == tracking_id]
            distribution = "Multi SKU" if len(trackers_with_same_id) > 1 else "Single SKU"
            
            # Format scan time
            scan_time = scan.get('timestamp', '')
            if scan_time:
                try:
                    dt = datetime.fromisoformat(scan_time.replace('Z', '+00:00'))
                    scan_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    scan_time = scan_time
            
            recent_scans.append({
                "id": str(scan.get('id', '')),
                "tracking_id": tracker_info.get('shipment_tracker', tracker_code),
                "platform": tracker_info.get('channel_name', 'Unknown'),
                "last_scan": "Label",
                "scan_status": scan_status,
                "distribution": distribution,
                "scan_time": scan_time,
                "amount": tracker_info.get('amount', 0),
                "buyer_city": tracker_info.get('buyer_city', 'Unknown'),
                "courier": tracker_info.get('courier', 'Unknown')
            })
        
        return {
            "results": recent_scans,
            "count": len(label_scans),
            "page": page,
            "limit": limit,
            "total_pages": (len(label_scans) + limit - 1) // limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent label scans: {str(e)}")

@app.get("/api/v1/scan/recent/packing")
async def get_recent_packing_scans(page: int = 1, limit: int = 20):
    """Get recent packing scans with pagination"""
    try:
        # Filter scans for packing type only
        packing_scans = [scan for scan in scans_db if scan.get('scan_type') in ['packing', 'packing_dual']]
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get recent packing scans with tracker details
        recent_scans = []
        for scan in packing_scans[offset:offset + limit]:
            tracker_code = scan.get('tracker_code', '')
            tracker_info = tracker_data.get(tracker_code, {})
            
            # Determine scan status
            scan_status = "Success" if scan.get('status', '') == 'completed' else "Error"
            
            # Determine distribution type
            tracking_id = tracker_info.get('shipment_tracker', '')
            trackers_with_same_id = [t for t in uploaded_trackers if tracker_data.get(t, {}).get('shipment_tracker') == tracking_id]
            distribution = "Multi SKU" if len(trackers_with_same_id) > 1 else "Single SKU"
            
            # Format scan time
            scan_time = scan.get('timestamp', '')
            if scan_time:
                try:
                    dt = datetime.fromisoformat(scan_time.replace('Z', '+00:00'))
                    scan_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    scan_time = scan_time
            
            recent_scans.append({
                "id": str(scan.get('id', '')),
                "tracking_id": tracker_info.get('shipment_tracker', tracker_code),
                "platform": tracker_info.get('channel_name', 'Unknown'),
                "last_scan": "Packing",
                "scan_status": scan_status,
                "distribution": distribution,
                "scan_time": scan_time,
                "amount": tracker_info.get('amount', 0),
                "buyer_city": tracker_info.get('buyer_city', 'Unknown'),
                "courier": tracker_info.get('courier', 'Unknown')
            })
        
        return {
            "results": recent_scans,
            "count": len(packing_scans),
            "page": page,
            "limit": limit,
            "total_pages": (len(packing_scans) + limit - 1) // limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent packing scans: {str(e)}")

@app.get("/api/v1/scan/recent/dispatch")
async def get_recent_dispatch_scans(page: int = 1, limit: int = 20):
    """Get recent dispatch scans with pagination"""
    try:
        # Filter scans for dispatch type only
        dispatch_scans = [scan for scan in scans_db if scan.get('scan_type') == 'dispatch']
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get recent dispatch scans with tracker details
        recent_scans = []
        for scan in dispatch_scans[offset:offset + limit]:
            tracker_code = scan.get('tracker_code', '')
            tracker_info = tracker_data.get(tracker_code, {})
            
            # Determine scan status
            scan_status = "Success" if scan.get('status', '') == 'completed' else "Error"
            
            # Determine distribution type
            tracking_id = tracker_info.get('shipment_tracker', '')
            trackers_with_same_id = [t for t in uploaded_trackers if tracker_data.get(t, {}).get('shipment_tracker') == tracking_id]
            distribution = "Multi SKU" if len(trackers_with_same_id) > 1 else "Single SKU"
            
            # Format scan time
            scan_time = scan.get('timestamp', '')
            if scan_time:
                try:
                    dt = datetime.fromisoformat(scan_time.replace('Z', '+00:00'))
                    scan_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    scan_time = scan_time
            
            recent_scans.append({
                "id": str(scan.get('id', '')),
                "tracking_id": tracker_info.get('shipment_tracker', tracker_code),
                "platform": tracker_info.get('channel_name', 'Unknown'),
                "last_scan": "Dispatch",
                "scan_status": scan_status,
                "distribution": distribution,
                "scan_time": scan_time,
                "amount": tracker_info.get('amount', 0),
                "buyer_city": tracker_info.get('buyer_city', 'Unknown'),
                "courier": tracker_info.get('courier', 'Unknown')
            })
        
        return {
            "results": recent_scans,
            "count": len(dispatch_scans),
            "page": page,
            "limit": limit,
            "total_pages": (len(dispatch_scans) + limit - 1) // limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent dispatch scans: {str(e)}")

# Add new API endpoints for Multi-SKU management

@app.post("/api/v1/system/fix-data/")
async def fix_data_structure():
    """Fix existing data structure"""
    fix_existing_data_structure()
    return {"message": "Data structure fixed successfully"}

# Startup fix
startup_fix()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 