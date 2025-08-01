#!/usr/bin/env python3
"""
FastAPI backend for Fulfillment Tracking System
Uses Firestore as the database - No local file storage
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from datetime import datetime
import uuid
import asyncio
import threading
import time

# Import Firestore service
from app.services.firestore_service import firestore_service
from app.services.gsheets_service import gsheets_service
from app.core.config import settings

app = FastAPI(title="Fulfillment Tracking API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    """Startup event to initialize services"""
    # Start Google Sheets sync scheduler
    start_gsheets_sync_scheduler()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080", 
        "https://zapscan-flow-frontend.vercel.app",
        "https://zapscan-flow.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class ScanRequest(BaseModel):
    tracker_code: str
    scan_type: str  # "label", "packing", "dispatch", "cancelled"

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
    last_updated: Optional[str] = None

class TrackerDataUpload(BaseModel):
    trackers: List[TrackerData]

class PackingDualScanRequest(BaseModel):
    tracker_code: str
    product_code: str  # G-Code or EAN-Code

class PackingScanRequest(BaseModel):
    tracker_code: str  # Tracking ID
    product_code: str  # G-Code or EAN-Code to match

class PendingShipmentRequest(BaseModel):
    tracking_id: str
    scan_type: str  # "packing" or "dispatch"
    reason: Optional[str] = None  # Optional reason for putting on hold

class UnholdShipmentRequest(BaseModel):
    tracking_id: str
    scan_type: str  # "packing" or "dispatch"

def get_trackers_by_tracking_id(tracking_id: str):
    """Get all trackers that belong to the same tracking ID (case-insensitive)"""
    trackers = []
    
    # Convert tracking_id to uppercase for case-insensitive matching
    tracking_id_upper = tracking_id.upper()
    
    # Get all tracker data
    all_tracker_data = firestore_service.get_all_tracker_data()
    
    # Find all trackers with the exact tracking_id (case-insensitive)
    for tracker_code, data in all_tracker_data.items():
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
    
    # Maintain original order (don't sort)
    return trackers

def validate_scan_prerequisites(tracking_id: str, scan_type: str):
    """Validate scan prerequisites for a tracking ID"""
    trackers = get_trackers_by_tracking_id(tracking_id)
    if not trackers:
        raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
    
    all_tracker_status = firestore_service.get_all_tracker_status()
    
    for tracker in trackers:
        tracker_code = tracker['tracker_code']
        tracker_status = all_tracker_status.get(tracker_code, {})
        
        if scan_type == "packing":
            # For packing, check if label scan is completed
            if not tracker_status.get("label", False):
                raise HTTPException(status_code=400, detail="Label scan must be completed before packing scan")
        elif scan_type == "dispatch":
            # For dispatch, check if both label and packing scans are completed
            if not tracker_status.get("label", False):
                raise HTTPException(status_code=400, detail="Label scan must be completed before dispatch scan")
            if not tracker_status.get("packing", False):
                raise HTTPException(status_code=400, detail="Packing scan must be completed before dispatch scan")
    
    return trackers

def scan_all_trackers_for_tracking_id(tracking_id: str, scan_type: str):
    """Scan all trackers for a given tracking ID at once (for label and dispatch)"""
    try:
        trackers = get_trackers_by_tracking_id(tracking_id)
        if not trackers:
            return None
        
        scanned_trackers = []
        scan_records = []
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            
            # For label and dispatch, scan ALL trackers regardless of current status
            # Create scan record
            scan_record = {
                "id": str(uuid.uuid4()),
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
            
            # Save scan to Firestore
            firestore_service.save_scan(scan_record)
            scan_records.append(scan_record)
            
            # Update tracker status for this specific SKU
            sanitized_tracker_code = get_sanitized_tracker_code(tracker_code)
            if sanitized_tracker_code not in all_tracker_status:
                all_tracker_status[sanitized_tracker_code] = {"label": False, "packing": False, "dispatch": False}
            all_tracker_status[sanitized_tracker_code][scan_type] = True
            firestore_service.save_tracker_status(sanitized_tracker_code, all_tracker_status[sanitized_tracker_code])
            
            scanned_trackers.append(tracker)
        
        # Update scan count and progress
        current_count = firestore_service.get_tracker_scan_count(tracking_id)
        if not current_count or not isinstance(current_count, dict):
            current_count = {}
        current_count[scan_type] = current_count.get(scan_type, 0) + len(scanned_trackers)
        firestore_service.save_tracker_scan_count(tracking_id, current_count)
        
        # Update progress for all scanned trackers
        update_scan_progress(tracking_id, scan_type)
        
        # Get updated progress
        progress = get_scan_progress(tracking_id, scan_type)
        
        return {
            "scanned_trackers": scanned_trackers,
            "scan_records": scan_records,
            "progress": progress,
            "total_scanned": len(scanned_trackers)
        }
    except Exception as e:
        print(f"Error in scan_all_trackers_for_tracking_id: {e}")
        print(f"tracking_id: {tracking_id}, scan_type: {scan_type}")
        raise e

def get_next_sku_to_scan(tracking_id: str, scan_type: str):
    """Get the next SKU to scan for a tracking ID with strict validation"""
    trackers = get_trackers_by_tracking_id(tracking_id)
    if not trackers:
        return None
    
    # Maintain original order (don't sort by channel_id)
    # trackers.sort(key=lambda x: x.get('channel_id', ''))
    
    all_tracker_status = firestore_service.get_all_tracker_status()
    
    # Find the next un-scanned tracker for this scan type
    for tracker in trackers:
        tracker_code = tracker['tracker_code']
        tracker_status = all_tracker_status.get(tracker_code, {})
        
        # Check prerequisites based on scan type
        if scan_type == "packing":
            # For packing, check if label scan is completed
            if not tracker_status.get("label", False):
                continue  # Skip this tracker, label not completed
        elif scan_type == "dispatch":
            # For dispatch, check if both label and packing scans are completed
            if not tracker_status.get("label", False):
                continue  # Skip this tracker, label not completed
            if not tracker_status.get("packing", False):
                continue  # Skip this tracker, packing not completed
        
        # Check if already scanned for this scan type
        if tracker_status.get(scan_type, False):
            continue  # Skip already scanned trackers
        
        # This tracker hasn't been scanned for this scan type yet and prerequisites are met
        return tracker
    
    # All trackers have been scanned for this scan type or prerequisites not met
    return None

def update_scan_progress(tracking_id: str, scan_type: str):
    """Update scan progress for a tracking ID"""
    try:
        trackers = get_trackers_by_tracking_id(tracking_id)
        
        if not trackers:
            return
        
        # Get current progress
        progress = firestore_service.get_tracker_scan_progress(tracking_id)
        if not progress or not isinstance(progress, dict):
            progress = {}
        
        # Count completed scans for this type
        completed_count = 0
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            status = all_tracker_status.get(tracker_code, {})
            if status.get(scan_type, False):
                completed_count += 1
        
        # Update progress
        progress[scan_type] = {
            'scanned': completed_count,
            'total': len(trackers)
        }
        
        firestore_service.save_tracker_scan_progress(tracking_id, progress)
    except Exception as e:
        print(f"Error in update_scan_progress: {e}")
        print(f"tracking_id: {tracking_id}, scan_type: {scan_type}")

def get_scan_progress(tracking_id: str, scan_type: str) -> dict:
    """Get scan progress for a tracking ID"""
    try:
        progress = firestore_service.get_tracker_scan_progress(tracking_id)
        if not progress or not isinstance(progress, dict):
            progress = {}
        return progress.get(scan_type, {'scanned': 0, 'total': 0})
    except Exception as e:
        print(f"Error in get_scan_progress: {e}")
        return {'scanned': 0, 'total': 0}

def sanitize_tracker_code(tracker_code: str) -> str:
    """Sanitize tracker code for Firestore document ID"""
    import re
    # Replace invalid characters with underscores
    # Firestore document IDs cannot contain: /, \, ., *, [, ], #, ?, @, :, <, >, |, space
    sanitized = re.sub(r'[\/\\\.\*\[\]\#\?\@\:\<\>\|\s]', '_', tracker_code)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'tracker_' + str(uuid.uuid4())[:8]
    return sanitized

def generate_unique_tracker_key(base_tracker_code: str, existing_keys: list) -> str:
    """Generate a unique tracker key"""
    sanitized_base = sanitize_tracker_code(base_tracker_code)
    if sanitized_base not in existing_keys:
        return sanitized_base
    
    counter = 1
    while f"{sanitized_base}_{counter}" in existing_keys:
        counter += 1
    
    return f"{sanitized_base}_{counter}"

def get_sanitized_tracker_code(original_tracker_code: str) -> str:
    """Get the sanitized version of a tracker code for Firestore operations"""
    return sanitize_tracker_code(original_tracker_code)

def sync_to_google_sheets():
    """Background task to sync data to Google Sheets"""
    try:
        all_tracker_data = firestore_service.get_all_tracker_data()
        if all_tracker_data:
            success = gsheets_service.sync_all_tracker_data(all_tracker_data)
            if success:
                print(f"Successfully synced {len(all_tracker_data)} trackers to Google Sheets")
            else:
                print("Failed to sync to Google Sheets")
        else:
            print("No tracker data to sync")
    except Exception as e:
        print(f"Error in Google Sheets sync: {e}")

def start_gsheets_sync_scheduler():
    """Start the Google Sheets sync scheduler"""
    def sync_scheduler():
        while True:
            try:
                sync_to_google_sheets()
                time.sleep(300)  # Sync every 5 minutes
            except Exception as e:
                print(f"Error in sync scheduler: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    # Start sync scheduler in a separate thread
    sync_thread = threading.Thread(target=sync_scheduler, daemon=True)
    sync_thread.start()
    print("Google Sheets sync scheduler started")

@app.get("/")
async def root():
    return {"message": "Fulfillment Tracking API with Firestore"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "firestore"}

@app.post("/api/v1/trackers/upload/")
async def upload_trackers(
    tracker_upload: TrackerUpload,
    duplicate_handling: str = Query("allow", description="How to handle duplicates: 'skip', 'allow', or 'update'")
):
    """Upload tracker codes with basic data and duplicate handling options"""
    try:
        # Validate duplicate handling parameter
        if duplicate_handling not in ["skip", "allow", "update"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid duplicate_handling. Must be 'skip', 'allow', or 'update'"
            )
        
        # Get existing uploaded trackers
        existing_trackers = firestore_service.get_uploaded_trackers()
        
        # Get all existing tracker data to check for tracking ID conflicts
        all_tracker_data = firestore_service.get_all_tracker_data()
        existing_tracking_ids = set()
        for tracker_code, data in all_tracker_data.items():
            existing_tracking_ids.add(data.get('shipment_tracker', '').upper())
        
        new_trackers = []
        skipped_trackers = []
        updated_trackers = []
        
        for tracker_code in tracker_upload.tracker_codes:
            base_tracking_id = tracker_code.upper()
            
            # Check if tracking ID already exists
            if base_tracking_id in existing_tracking_ids:
                if duplicate_handling == "skip":
                    skipped_trackers.append(tracker_code)
                    continue
                elif duplicate_handling == "update":
                    # Find existing tracker code for this tracking ID
                    existing_tracker_code = None
                    for code, data in all_tracker_data.items():
                        if data.get('shipment_tracker', '').upper() == base_tracking_id:
                            existing_tracker_code = code
                            break
                    
                    if existing_tracker_code:
                        # Update existing tracker data
                        basic_tracker_data = {
                            'shipment_tracker': tracker_code,
                            'tracker_code': tracker_code,
                            'channel_name': 'Unknown',
                            'courier': 'Unknown',
                            'g_code': tracker_code,
                            'ean_code': tracker_code,
                            'product_sku_code': 'Unknown',
                            'channel_id': 'Unknown',
                            'qty': 1,
                            'amount': 0.0,
                            'payment_mode': 'Unknown',
                            'order_status': 'Pending',
                            'buyer_city': 'Unknown',
                            'buyer_state': 'Unknown',
                            'buyer_pincode': 'Unknown',
                            'invoice_number': 'Unknown'
                        }
                        firestore_service.save_tracker_data(existing_tracker_code, basic_tracker_data)
                        updated_trackers.append(tracker_code)
                        continue
            
            # Always generate unique document ID for Firestore to avoid overwriting
            import time
            timestamp = int(time.time() * 1000)  # milliseconds
            random_suffix = str(uuid.uuid4())[:8]  # 8 characters from UUID
            unique_doc_id = f"{sanitize_tracker_code(tracker_code)}_{timestamp}_{random_suffix}"
            
            new_trackers.append(unique_doc_id)
            
            # Create basic tracker data
            basic_tracker_data = {
                'shipment_tracker': tracker_code,  # Keep original tracking ID
                'tracker_code': tracker_code,      # Keep original tracker code
                'channel_name': 'Unknown',
                'courier': 'Unknown',
                'g_code': tracker_code,
                'ean_code': tracker_code,
                'product_sku_code': 'Unknown',
                'channel_id': 'Unknown',
                'qty': 1,
                'amount': 0.0,
                'payment_mode': 'Unknown',
                'order_status': 'Pending',
                'buyer_city': 'Unknown',
                'buyer_state': 'Unknown',
                'buyer_pincode': 'Unknown',
                'invoice_number': 'Unknown'
            }
            
            # Save tracker data to Firestore using unique document ID
            firestore_service.save_tracker_data(unique_doc_id, basic_tracker_data)
            
            # Initialize tracker status
            firestore_service.save_tracker_status(unique_doc_id, {
                'label': False,
                'packing': False,
                'dispatch': False
            })
        
        # Update uploaded trackers list
        all_trackers = existing_trackers + new_trackers
        firestore_service.save_uploaded_trackers(all_trackers)
        
        # Create appropriate message based on duplicate handling
        if duplicate_handling == "skip":
            message = f"Processed {len(tracker_upload.tracker_codes)} trackers. {len(new_trackers)} created, {len(skipped_trackers)} skipped (duplicates)."
        elif duplicate_handling == "update":
            message = f"Processed {len(tracker_upload.tracker_codes)} trackers. {len(new_trackers)} created, {len(updated_trackers)} updated."
        else:  # allow
            message = f"Successfully uploaded {len(new_trackers)} new trackers with basic data"
        
        return {
            "message": message,
            "new_trackers": new_trackers,
            "skipped_trackers": skipped_trackers,
            "updated_trackers": updated_trackers,
            "total_trackers": len(all_trackers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/trackers/upload-detailed/")
async def upload_detailed_trackers(
    tracker_data_upload: TrackerDataUpload,
    duplicate_handling: str = Query("allow", description="How to handle duplicates: 'skip', 'allow', or 'update'")
):
    """Upload detailed tracker data with proper multi-SKU handling and duplicate options"""
    try:
        # Validate duplicate handling parameter
        if duplicate_handling not in ["skip", "allow", "update"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid duplicate_handling. Must be 'skip', 'allow', or 'update'"
            )
        
        # Get existing uploaded trackers
        existing_trackers = firestore_service.get_uploaded_trackers()
        
        # Get all existing tracker data to check for tracking ID conflicts
        all_tracker_data = firestore_service.get_all_tracker_data()
        existing_tracking_ids = set()
        for tracker_code, data in all_tracker_data.items():
            existing_tracking_ids.add(data.get('shipment_tracker', '').upper())
        
        new_trackers = []
        skipped_trackers = []
        updated_trackers = []
        processed_tracking_id_product_combinations = set()  # Track unique tracking ID + product combinations
        
        for tracker_data in tracker_data_upload.trackers:
            base_tracking_id = tracker_data.shipment_tracker.upper()
            product_sku = tracker_data.product_sku_code or 'Unknown'
            
            # Create unique combination of tracking ID + product SKU
            tracking_product_key = f"{base_tracking_id}_{product_sku}"
            
            # Check if this exact tracking ID + product combination was already processed in this batch
            if tracking_product_key in processed_tracking_id_product_combinations:
                if duplicate_handling == "skip":
                    skipped_trackers.append(f"{tracker_data.shipment_tracker} ({product_sku})")
                    continue
                elif duplicate_handling == "update":
                    # For update mode, skip exact duplicates within batch
                    skipped_trackers.append(f"{tracker_data.shipment_tracker} ({product_sku})")
                    continue
                # For "allow" mode, continue to create new tracker
            
            # Check if tracking ID already exists in database
            if base_tracking_id in existing_tracking_ids:
                if duplicate_handling == "skip":
                    skipped_trackers.append(tracker_data.shipment_tracker)
                    continue
                elif duplicate_handling == "update":
                    # Find existing tracker code for this tracking ID
                    existing_tracker_code = None
                    for code, data in all_tracker_data.items():
                        if data.get('shipment_tracker', '').upper() == base_tracking_id:
                            existing_tracker_code = code
                            break
                    
                    if existing_tracker_code:
                        # Update existing tracker data with timestamp
                        tracker_dict = tracker_data.dict()
                        tracker_dict['shipment_tracker'] = tracker_data.shipment_tracker
                        tracker_dict['tracker_code'] = existing_tracker_code
                        tracker_dict['last_updated'] = datetime.now().isoformat()  # Add timestamp
                        firestore_service.save_tracker_data(existing_tracker_code, tracker_dict)
                        updated_trackers.append(tracker_data.shipment_tracker)
                        processed_tracking_id_product_combinations.add(tracking_product_key)
                        continue
                # For "allow" mode, continue to create new tracker with unique code
            
            # Always generate unique document ID for Firestore to avoid overwriting
            import time
            timestamp = int(time.time() * 1000)  # milliseconds
            random_suffix = str(uuid.uuid4())[:8]  # 8 characters from UUID
            unique_doc_id = f"{sanitize_tracker_code(tracker_data.shipment_tracker)}_{timestamp}_{random_suffix}"
            
            # Save tracker data with timestamp
            tracker_dict = tracker_data.dict()
            tracker_dict['shipment_tracker'] = tracker_data.shipment_tracker  # Keep original tracking ID
            tracker_dict['tracker_code'] = tracker_data.shipment_tracker  # Keep original tracker code
            tracker_dict['last_updated'] = datetime.now().isoformat()  # Add timestamp
            firestore_service.save_tracker_data(unique_doc_id, tracker_dict)
            
            # Initialize tracker status
            firestore_service.save_tracker_status(unique_doc_id, {
                'label': False,
                'packing': False,
                'dispatch': False
            })
            
            # Add to new trackers list
            new_trackers.append(unique_doc_id)
            
            # Mark this tracking ID + product combination as processed in this batch
            processed_tracking_id_product_combinations.add(tracking_product_key)
        
        # Update uploaded trackers list
        all_trackers = existing_trackers + new_trackers
        firestore_service.save_uploaded_trackers(all_trackers)
        
        # Create appropriate message based on duplicate handling
        if duplicate_handling == "skip":
            message = f"Processed {len(tracker_data_upload.trackers)} tracker entries. {len(new_trackers)} created, {len(skipped_trackers)} skipped (duplicates)."
        elif duplicate_handling == "update":
            message = f"Processed {len(tracker_data_upload.trackers)} tracker entries. {len(new_trackers)} created, {len(updated_trackers)} updated."
        else:  # allow
            message = f"Successfully uploaded {len(new_trackers)} tracker entries with detailed data"
        
        return {
            "message": message,
            "new_trackers": new_trackers,
            "skipped_trackers": skipped_trackers,
            "updated_trackers": updated_trackers,
            "uploaded_count": len(new_trackers),
            "total_trackers": len(all_trackers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/trackers/uploaded/")
async def get_uploaded_trackers():
    """Get all uploaded trackers"""
    try:
        trackers = firestore_service.get_uploaded_trackers()
        return {"uploaded_trackers": trackers, "count": len(trackers)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scan/label/")
async def process_label_scan(scan_request: ScanRequest):
    """Process label scan - scan ALL trackers for tracking ID at once"""
    try:
        tracking_id = scan_request.tracker_code
        
        # Check if tracking ID exists in tracker data
        trackers = get_trackers_by_tracking_id(tracking_id)
        if not trackers:
            raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
        
        # Check if label scan is already completed for all trackers
        all_tracker_status = firestore_service.get_all_tracker_status()
        all_label_scanned = True
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            sanitized_tracker_code = get_sanitized_tracker_code(tracker_code)
            tracker_status = all_tracker_status.get(sanitized_tracker_code, {})
            if not tracker_status.get("label", False):
                all_label_scanned = False
                break
        
        if all_label_scanned:
            raise HTTPException(status_code=400, detail="Label scan already completed for all SKUs in this tracking ID")
        
        # Scan ALL trackers for this tracking ID at once (regardless of current status)
        scan_result = scan_all_trackers_for_tracking_id(tracking_id, "label")
        if not scan_result:
            raise HTTPException(status_code=400, detail="No trackers found for this tracking ID")
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scan/packing/")
async def process_packing_scan(scan_request: ScanRequest):
    """Process a packing scan with automatic unhold capability"""
    try:
        tracker_code = scan_request.tracker_code
        scan_type = scan_request.scan_type
        
        # Get all trackers for this tracking ID
        trackers = get_trackers_by_tracking_id(tracker_code)
        if not trackers:
            raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
        
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        # Check if any trackers are on hold for packing
        hold_trackers = []
        normal_trackers = []
        
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            sanitized_tracker_code = get_sanitized_tracker_code(tracker_code)
            tracker_status = all_tracker_status.get(sanitized_tracker_code, {})
            
            if tracker_status.get("pending", False):
                # Check if it's on hold for packing (label done but packing not done)
                if tracker_status.get("label", False) and not tracker_status.get("packing", False):
                    hold_trackers.append((sanitized_tracker_code, tracker_status))
                else:
                    normal_trackers.append((sanitized_tracker_code, tracker_status))
            else:
                normal_trackers.append((sanitized_tracker_code, tracker_status))
        
        # Process hold trackers first (unhold them)
        unhold_count = 0
        for sanitized_tracker_code, tracker_status in hold_trackers:
            # Unhold and complete packing scan
            tracker_status["pending"] = False
            tracker_status["packing"] = True
            firestore_service.save_tracker_status(sanitized_tracker_code, tracker_status)
            unhold_count += 1
        
        # Process normal trackers (regular packing scan)
        scan_count = 0
        for sanitized_tracker_code, tracker_status in normal_trackers:
            # Validate prerequisites
            if not tracker_status.get("label", False):
                raise HTTPException(status_code=400, detail=f"Label scan must be completed before packing scan for tracker {sanitized_tracker_code}")
            
            if tracker_status.get("packing", False):
                raise HTTPException(status_code=400, detail=f"Packing scan already completed for tracker {sanitized_tracker_code}")
            
            # Complete packing scan
            tracker_status["packing"] = True
            firestore_service.save_tracker_status(sanitized_tracker_code, tracker_status)
            scan_count += 1
        
        # Update scan counts
        current_count = firestore_service.get_tracker_scan_count(tracker_code) or {}
        current_count["packing"] = current_count.get("packing", 0) + scan_count + unhold_count
        current_count["pending"] = max(0, current_count.get("pending", 0) - unhold_count)
        firestore_service.save_tracker_scan_count(tracker_code, current_count)
        
        # Update scan progress
        update_scan_progress(tracker_code, "packing")
        
        # Save scan record
        # Get complete tracker data for the first tracker to populate scan record details
        all_tracker_data = firestore_service.get_all_tracker_data()
        first_tracker_code = trackers[0]['tracker_code'] if trackers else None
        first_tracker_data = all_tracker_data.get(first_tracker_code, {}) if first_tracker_code else {}
        
        scan_record = {
            "tracking_id": tracker_code,
            "scan_type": "packing",
            "action": "unhold_complete" if unhold_count > 0 else "scan",
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "platform": first_tracker_data.get('channel_name', 'Unknown'),
            "amount": first_tracker_data.get('amount', 0),
            "buyer_city": first_tracker_data.get('buyer_city', 'Unknown'),
            "courier": first_tracker_data.get('courier', 'Unknown'),
            "distribution": "Single SKU" if len(trackers) == 1 else "Multi SKU",
            "scan_status": "Success",
            "status": "completed"  # Add this field for compatibility with recent scans endpoint
        }
        firestore_service.save_scan(scan_record)
        
        # Return appropriate message
        if unhold_count > 0 and scan_count > 0:
            message = f"Shipment unhold and {scan_count} new items scanned. Total {unhold_count + scan_count} items processed."
        elif unhold_count > 0:
            message = f"Shipment unhold and packing scan completed successfully! {unhold_count} items processed."
        else:
            message = f"Packing scan completed successfully! {scan_count} items scanned."
        
        return {
            "message": message,
            "tracking_id": tracker_code,
            "scan_type": "packing",
            "scanned_count": scan_count,
            "unhold_count": unhold_count,
            "total_processed": scan_count + unhold_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scan/packing-with-product/")
async def process_packing_with_product_scan(scan_request: PackingScanRequest):
    """Process packing scan with product code matching"""
    try:
        tracking_id = scan_request.tracker_code
        product_code = scan_request.product_code
        
        # Validate prerequisites (label scan must be completed)
        validate_scan_prerequisites(tracking_id, "packing")
        
        # Get all trackers for this tracking ID
        trackers = get_trackers_by_tracking_id(tracking_id)
        if not trackers:
            raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
        
        # Find the tracker that matches the product code
        matching_tracker = None
        for tracker in trackers:
            g_code = tracker['g_code']
            ean_code = tracker['ean_code']
            
            if product_code in [g_code, ean_code]:
                matching_tracker = tracker
                break
        
        if not matching_tracker:
            raise HTTPException(
                status_code=400, 
                detail=f"Product code {product_code} does not match any SKU for tracking ID {tracking_id}"
            )
        
        tracker_code = matching_tracker['tracker_code']
        
        # Allow re-scanning for packing (don't check if already scanned)
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        # Create scan record
        scan_record = {
            "id": str(uuid.uuid4()),
            "tracker_code": tracker_code,
            "tracking_id": tracking_id,
            "scan_type": "packing",
            "product_code": product_code,
            "sku_details": {
                "g_code": matching_tracker['g_code'],
                "ean_code": matching_tracker['ean_code'],
                "product_sku_code": matching_tracker['product_sku_code'],
                "channel_id": matching_tracker['channel_id']
            },
            "timestamp": datetime.now().isoformat(),
            "status": "completed"
        }
        
        # Save scan to Firestore
        firestore_service.save_scan(scan_record)
        
        # Update tracker status for this specific SKU
        if tracker_code not in all_tracker_status:
            all_tracker_status[tracker_code] = {"label": False, "packing": False, "dispatch": False}
        all_tracker_status[tracker_code]["packing"] = True
        firestore_service.save_tracker_status(tracker_code, all_tracker_status[tracker_code])
        
        # Update scan count and progress
        current_count = firestore_service.get_tracker_scan_count(tracking_id)
        if not current_count or not isinstance(current_count, dict):
            current_count = {}
        current_count["packing"] = current_count.get("packing", 0) + 1
        firestore_service.save_tracker_scan_count(tracking_id, current_count)
        
        # Update scan progress
        update_scan_progress(tracking_id, "packing")
        
        # Get updated progress
        progress = get_scan_progress(tracking_id, "packing")
        
        return {
            "message": f"Packing scan completed for SKU: {matching_tracker['product_sku_code']} (Product: {product_code})",
            "scan": scan_record,
            "sku_scanned": {
                "g_code": matching_tracker['g_code'],
                "ean_code": matching_tracker['ean_code'],
                "product_sku_code": matching_tracker['product_sku_code'],
                "channel_id": matching_tracker['channel_id']
            },
            "progress": progress,
            "next_step": "dispatch" if progress["scanned"] >= progress["total"] else "packing",
            "matched_product": {
                "g_code": matching_tracker['g_code'],
                "ean_code": matching_tracker['ean_code'],
                "scanned_code": product_code
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scan/packing-dual/")
async def process_packing_dual_scan(scan_request: PackingDualScanRequest):
    """Process packing dual scan with strict workflow validation"""
    try:
        tracking_id = scan_request.tracker_code
        product_code = scan_request.product_code
        
        # Validate prerequisites (label scan must be completed)
        validate_scan_prerequisites(tracking_id, "packing")
        
        # Get the next SKU to scan for packing
        next_sku = get_next_sku_to_scan(tracking_id, "packing")
        if not next_sku:
            raise HTTPException(status_code=400, detail="All SKUs for this tracking ID have been scanned")
        
        tracker_code = next_sku['tracker_code']
        
        # Check if already scanned
        all_tracker_status = firestore_service.get_all_tracker_status()
        tracker_status = all_tracker_status.get(tracker_code, {})
        if tracker_status.get("packing", False):
            raise HTTPException(status_code=400, detail="Packing scan already completed for this SKU")
        
        # Validate product code (check if it matches the tracker's product)
        g_code = next_sku['g_code']
        ean_code = next_sku['ean_code']
        
        if product_code not in [g_code, ean_code]:
            raise HTTPException(
                status_code=400, 
                detail=f"Product code {product_code} does not match tracker's G-Code ({g_code}) or EAN-Code ({ean_code})"
            )
        
        # Create scan record
        scan_record = {
            "id": str(uuid.uuid4()),
            "tracker_code": tracker_code,
            "tracking_id": tracking_id,
            "scan_type": "packing",
            "product_code": product_code,
            "sku_details": {
                "g_code": g_code,
                "ean_code": ean_code,
                "product_sku_code": next_sku['product_sku_code'],
                "channel_id": next_sku['channel_id']
            },
            "timestamp": datetime.now().isoformat(),
            "status": "completed"
        }
        
        # Save scan to Firestore
        firestore_service.save_scan(scan_record)
        
        # Update tracker status for this specific SKU
        if tracker_code not in all_tracker_status:
            all_tracker_status[tracker_code] = {"label": False, "packing": False, "dispatch": False}
        all_tracker_status[tracker_code]["packing"] = True
        firestore_service.save_tracker_status(tracker_code, all_tracker_status[tracker_code])
        
        # Update scan count and progress
        current_count = firestore_service.get_tracker_scan_count(tracking_id)
        if not current_count or not isinstance(current_count, dict):
            current_count = {}
        current_count["packing"] = current_count.get("packing", 0) + 1
        firestore_service.save_tracker_scan_count(tracking_id, current_count)
        
        # Update scan progress
        update_scan_progress(tracking_id, "packing")
        
        # Get updated progress
        progress = get_scan_progress(tracking_id, "packing")
        
        return {
            "message": f"Packing dual scan completed for SKU: {next_sku['product_sku_code']}",
            "scan": scan_record,
            "sku_scanned": {
                "g_code": g_code,
                "ean_code": ean_code,
                "product_sku_code": next_sku['product_sku_code'],
                "channel_id": next_sku['channel_id']
            },
            "progress": progress,
            "next_step": "dispatch" if progress["scanned"] < progress["total"] else "dispatch",
            "matched_product": {
                "g_code": g_code,
                "ean_code": ean_code,
                "scanned_code": product_code
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scan/dispatch/")
async def process_dispatch_scan(scan_request: ScanRequest):
    """Process a dispatch scan with automatic unhold capability"""
    try:
        tracker_code = scan_request.tracker_code
        scan_type = scan_request.scan_type
        
        # Get all trackers for this tracking ID
        trackers = get_trackers_by_tracking_id(tracker_code)
        if not trackers:
            raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
        
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        # Check if any trackers are on hold for dispatch
        hold_trackers = []
        normal_trackers = []
        
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            sanitized_tracker_code = get_sanitized_tracker_code(tracker_code)
            tracker_status = all_tracker_status.get(sanitized_tracker_code, {})
            
            if tracker_status.get("pending", False):
                # Check if it's on hold for dispatch (label and packing done but dispatch not done)
                if tracker_status.get("label", False) and tracker_status.get("packing", False) and not tracker_status.get("dispatch", False):
                    hold_trackers.append((sanitized_tracker_code, tracker_status))
                else:
                    normal_trackers.append((sanitized_tracker_code, tracker_status))
            else:
                normal_trackers.append((sanitized_tracker_code, tracker_status))
        
        # Process hold trackers first (unhold them)
        unhold_count = 0
        for sanitized_tracker_code, tracker_status in hold_trackers:
            # Unhold and complete dispatch scan
            tracker_status["pending"] = False
            tracker_status["dispatch"] = True
            firestore_service.save_tracker_status(sanitized_tracker_code, tracker_status)
            unhold_count += 1
        
        # Process normal trackers (regular dispatch scan)
        scan_count = 0
        for sanitized_tracker_code, tracker_status in normal_trackers:
            # Skip if already completed
            if tracker_status.get("dispatch", False):
                continue
            
            # Enforce workflow: Label -> Packing -> Dispatch
            if not tracker_status.get("label", False):
                raise HTTPException(status_code=400, detail=f"Label scan must be completed before dispatch scan for tracker {sanitized_tracker_code}")
            
            if not tracker_status.get("packing", False):
                raise HTTPException(status_code=400, detail=f"Packing scan must be completed before dispatch scan for tracker {sanitized_tracker_code}")
            
            # Complete dispatch scan
            tracker_status["dispatch"] = True
            firestore_service.save_tracker_status(sanitized_tracker_code, tracker_status)
            scan_count += 1
        
        # If no trackers were processed, return error
        if scan_count == 0 and unhold_count == 0:
            raise HTTPException(status_code=400, detail="No trackers found to process for dispatch scan")
        
        # Update scan counts
        current_count = firestore_service.get_tracker_scan_count(tracker_code) or {}
        current_count["dispatch"] = current_count.get("dispatch", 0) + scan_count + unhold_count
        current_count["pending"] = max(0, current_count.get("pending", 0) - unhold_count)
        firestore_service.save_tracker_scan_count(tracker_code, current_count)
        
        # Update scan progress
        update_scan_progress(tracker_code, "dispatch")
        
        # Save scan record
        # Get complete tracker data for the first tracker to populate scan record details
        all_tracker_data = firestore_service.get_all_tracker_data()
        first_tracker_code = trackers[0]['tracker_code'] if trackers else None
        first_tracker_data = all_tracker_data.get(first_tracker_code, {}) if first_tracker_code else {}
        
        scan_record = {
            "tracking_id": tracker_code,
            "scan_type": "dispatch",
            "action": "unhold_complete" if unhold_count > 0 else "scan",
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "platform": first_tracker_data.get('channel_name', 'Unknown'),
            "amount": first_tracker_data.get('amount', 0),
            "buyer_city": first_tracker_data.get('buyer_city', 'Unknown'),
            "courier": first_tracker_data.get('courier', 'Unknown'),
            "distribution": "Single SKU" if len(trackers) == 1 else "Multi SKU",
            "scan_status": "Success",
            "status": "completed"  # Add this field for compatibility with recent scans endpoint
        }
        firestore_service.save_scan(scan_record)
        
        # Return appropriate message
        if unhold_count > 0 and scan_count > 0:
            message = f"Shipment unhold and {scan_count} new items scanned. Total {unhold_count + scan_count} items processed."
        elif unhold_count > 0:
            message = f"Shipment unhold and dispatch scan completed successfully! {unhold_count} items processed."
        else:
            message = f"Dispatch scan completed successfully! {scan_count} items scanned."
        
        return {
            "message": message,
            "tracking_id": tracker_code,
            "scan_type": "dispatch",
            "scanned_count": scan_count,
            "unhold_count": unhold_count,
            "total_processed": scan_count + unhold_count
        }
        
    except Exception as e:
        # Log the error for debugging
        print(f"Dispatch scan error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scan/cancelled/")
async def process_cancelled_shipment(scan_request: ScanRequest):
    """Process cancelled shipment - can be called before or after dispatch"""
    try:
        tracking_id = scan_request.tracker_code
        
        # Check if tracking ID exists in tracker data
        trackers = get_trackers_by_tracking_id(tracking_id)
        if not trackers:
            raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
        
        # Check if already cancelled
        all_tracker_status = firestore_service.get_all_tracker_status()
        all_cancelled = True
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            sanitized_tracker_code = get_sanitized_tracker_code(tracker_code)
            tracker_status = all_tracker_status.get(sanitized_tracker_code, {})
            if not tracker_status.get("cancelled", False):
                all_cancelled = False
                break
        
        if all_cancelled:
            raise HTTPException(status_code=400, detail="Shipment already cancelled for all SKUs in this tracking ID")
        
        # Process cancellation for all trackers
        cancelled_trackers = []
        scan_records = []
        
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            
            # Create cancellation record
            cancellation_record = {
                "id": str(uuid.uuid4()),
                "tracker_code": tracker_code,
                "tracking_id": tracking_id,
                "scan_type": "cancelled",
                "sku_details": {
                    "g_code": tracker['g_code'],
                    "ean_code": tracker['ean_code'],
                    "product_sku_code": tracker['product_sku_code'],
                    "channel_id": tracker['channel_id']
                },
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
                "cancellation_reason": "Shipment cancelled by user"
            }
            
            # Save cancellation to Firestore
            firestore_service.save_scan(cancellation_record)
            scan_records.append(cancellation_record)
            
            # Update tracker status - mark as cancelled and preserve previous statuses
            sanitized_tracker_code = get_sanitized_tracker_code(tracker_code)
            if sanitized_tracker_code not in all_tracker_status:
                all_tracker_status[sanitized_tracker_code] = {"label": False, "packing": False, "dispatch": False, "cancelled": False}
            
            # Mark as cancelled but preserve previous statuses to show the transition
            all_tracker_status[sanitized_tracker_code]["cancelled"] = True
            # Don't reset other statuses - keep them to show the progression
            # all_tracker_status[sanitized_tracker_code]["label"] = False
            # all_tracker_status[sanitized_tracker_code]["packing"] = False
            # all_tracker_status[sanitized_tracker_code]["dispatch"] = False
            all_tracker_status[sanitized_tracker_code]["pending"] = False
            
            firestore_service.save_tracker_status(sanitized_tracker_code, all_tracker_status[sanitized_tracker_code])
            
            cancelled_trackers.append(tracker)
        
        # Get complete tracker data for the first tracker to populate scan record details
        all_tracker_data = firestore_service.get_all_tracker_data()
        first_tracker_code = trackers[0]['tracker_code'] if trackers else None
        first_tracker_data = all_tracker_data.get(first_tracker_code, {}) if first_tracker_code else {}
        
        # Determine the previous stage for the first tracker
        first_sanitized_tracker_code = get_sanitized_tracker_code(first_tracker_code) if first_tracker_code else None
        first_tracker_status = all_tracker_status.get(first_sanitized_tracker_code, {}) if first_sanitized_tracker_code else {}
        
        # Determine previous stage
        if first_tracker_status.get("dispatch", False):
            previous_stage = "Dispatch"
        elif first_tracker_status.get("packing", False):
            previous_stage = "Packing"
        elif first_tracker_status.get("label", False):
            previous_stage = "Label"
        else:
            previous_stage = "Pre-Processing"
        
        # Create main cancellation scan record
        cancellation_scan_record = {
            "tracking_id": tracking_id,
            "scan_type": "cancelled",
            "action": "cancellation",
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "platform": first_tracker_data.get('channel_name', 'Unknown'),
            "amount": first_tracker_data.get('amount', 0),
            "buyer_city": first_tracker_data.get('buyer_city', 'Unknown'),
            "courier": first_tracker_data.get('courier', 'Unknown'),
            "distribution": "Single SKU" if len(trackers) == 1 else "Multi SKU",
            "scan_status": "Success",
            "status": "completed",
            "cancellation_reason": "Shipment cancelled by user",
            "previous_stage": previous_stage,
            "stage_transition": f"{previous_stage} → Cancelled"
        }
        firestore_service.save_scan(cancellation_scan_record)
        
        # Get the first cancelled SKU for response
        first_cancelled = cancelled_trackers[0] if cancelled_trackers else None
        
        return {
            "message": f"Shipment cancelled for {len(cancelled_trackers)} SKU(s)",
            "scan": cancellation_scan_record,
            "sku_cancelled": {
                "g_code": first_cancelled['g_code'] if first_cancelled else None,
                "ean_code": first_cancelled['ean_code'] if first_cancelled else None,
                "product_sku_code": first_cancelled['product_sku_code'] if first_cancelled else None,
                "channel_id": first_cancelled['channel_id'] if first_cancelled else None
            },
            "total_cancelled": len(cancelled_trackers),
            "cancellation_reason": "Shipment cancelled by user"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scan/pending/")
async def process_pending_shipment(pending_request: PendingShipmentRequest):
    """Process a pending shipment by putting it on hold"""
    try:
        tracking_id = pending_request.tracking_id
        scan_type = pending_request.scan_type
        
        trackers = get_trackers_by_tracking_id(tracking_id)
        if not trackers:
            raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
        
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        # Validate workflow before allowing hold
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            tracker_status = all_tracker_status.get(tracker_code, {})
            
            # Check if already on hold
            if tracker_status.get("pending", False):
                raise HTTPException(status_code=400, detail=f"Shipment for tracking ID {tracking_id} is already on hold for {scan_type}")
            
            # Validate workflow prerequisites
            if scan_type == "packing":
                # For packing hold: must have label scan completed
                if not tracker_status.get("label", False):
                    raise HTTPException(status_code=400, detail=f"Label scan must be completed before putting on hold for packing. Tracker: {tracker_code}")
                if tracker_status.get("packing", False):
                    raise HTTPException(status_code=400, detail=f"Packing scan already completed for tracker {tracker_code}")
                    
            elif scan_type == "dispatch":
                # For dispatch hold: must have label and packing scans completed
                if not tracker_status.get("label", False):
                    raise HTTPException(status_code=400, detail=f"Label scan must be completed before putting on hold for dispatch. Tracker: {tracker_code}")
                if not tracker_status.get("packing", False):
                    raise HTTPException(status_code=400, detail=f"Packing scan must be completed before putting on hold for dispatch. Tracker: {tracker_code}")
                if tracker_status.get("dispatch", False):
                    raise HTTPException(status_code=400, detail=f"Dispatch scan already completed for tracker {tracker_code}")
        
        # Put trackers on hold
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            if tracker_code not in all_tracker_status:
                all_tracker_status[tracker_code] = {"label": False, "packing": False, "dispatch": False, "pending": True}
            else:
                all_tracker_status[tracker_code]["pending"] = True
            firestore_service.save_tracker_status(tracker_code, all_tracker_status[tracker_code])
        
        current_count = firestore_service.get_tracker_scan_count(tracking_id) or {}
        current_count["pending"] = current_count.get("pending", 0) + len(trackers)
        firestore_service.save_tracker_scan_count(tracking_id, current_count)
        
        update_scan_progress(tracking_id, "pending")
        
        # Save scan record for recent activities
        # Get complete tracker data for the first tracker to populate scan record details
        all_tracker_data = firestore_service.get_all_tracker_data()
        first_tracker_code = trackers[0]['tracker_code'] if trackers else None
        first_tracker_data = all_tracker_data.get(first_tracker_code, {}) if first_tracker_code else {}
        
        scan_record = {
            "tracking_id": tracking_id,
            "scan_type": "pending",
            "action": "hold",
            "hold_stage": scan_type,  # Add the stage where it's on hold (packing/dispatch)
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "platform": first_tracker_data.get('channel_name', 'Unknown'),
            "amount": first_tracker_data.get('amount', 0),
            "buyer_city": first_tracker_data.get('buyer_city', 'Unknown'),
            "courier": first_tracker_data.get('courier', 'Unknown'),
            "distribution": "Single SKU" if len(trackers) == 1 else "Multi SKU",
            "scan_status": "Success",
            "items_count": len(trackers),  # Add count of items on hold
            "reason": pending_request.reason,  # Include reason if provided
            "status": "completed"  # Add for compatibility
        }
        firestore_service.save_scan(scan_record)
        
        return {
            "message": f"Shipment for tracking ID {tracking_id} has been put on hold for {scan_type}.",
            "tracking_id": tracking_id,
            "scan_type": scan_type,
            "pending_count": len(trackers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scan/unhold/")
async def process_unhold_shipment(unhold_request: UnholdShipmentRequest):
    """Process an unhold shipment by removing it from hold and completing the scan"""
    try:
        tracking_id = unhold_request.tracking_id
        scan_type = unhold_request.scan_type
        
        trackers = get_trackers_by_tracking_id(tracking_id)
        if not trackers:
            raise HTTPException(status_code=400, detail="Tracking ID not found in uploaded data")
        
        all_tracker_status = firestore_service.get_all_tracker_status()
        unhold_count = 0
        
        # First, check if any trackers are on hold and validate scan type
        hold_scan_types = set()
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            sanitized_tracker_code = get_sanitized_tracker_code(tracker_code)
            tracker_status = all_tracker_status.get(sanitized_tracker_code, {})
            
            if tracker_status.get("pending", False):
                # Determine what scan type this tracker is on hold for
                if tracker_status.get("label", False) and not tracker_status.get("packing", False):
                    hold_scan_types.add("packing")
                elif tracker_status.get("label", False) and tracker_status.get("packing", False) and not tracker_status.get("dispatch", False):
                    hold_scan_types.add("dispatch")
                else:
                    hold_scan_types.add("packing")  # Default to packing if unclear
        
        # Validate that we're unholding in the correct scan type
        if hold_scan_types and scan_type not in hold_scan_types:
            expected_types = ", ".join(hold_scan_types)
            raise HTTPException(
                status_code=400, 
                detail=f"Shipment for tracking ID {tracking_id} is on hold for {expected_types} scan. Please unhold in the correct scan type."
            )
        
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            sanitized_tracker_code = get_sanitized_tracker_code(tracker_code)
            tracker_status = all_tracker_status.get(sanitized_tracker_code, {})
            
            # Check if this tracker is on hold
            if tracker_status.get("pending", False):
                # Remove from hold
                tracker_status["pending"] = False
                
                # Complete the scan for the current scan type
                if scan_type == "packing":
                    tracker_status["packing"] = True
                elif scan_type == "dispatch":
                    tracker_status["dispatch"] = True
                
                # Save the updated status
                firestore_service.save_tracker_status(sanitized_tracker_code, tracker_status)
                unhold_count += 1
        
        if unhold_count == 0:
            raise HTTPException(status_code=400, detail=f"No shipments found on hold for tracking ID {tracking_id}")
        
        # Update scan count - remove from pending and add to the completed scan type
        current_count = firestore_service.get_tracker_scan_count(tracking_id) or {}
        current_count["pending"] = max(0, current_count.get("pending", 0) - unhold_count)
        
        # Add to the completed scan type count
        if scan_type == "packing":
            current_count["packing"] = current_count.get("packing", 0) + unhold_count
        elif scan_type == "dispatch":
            current_count["dispatch"] = current_count.get("dispatch", 0) + unhold_count
        
        firestore_service.save_tracker_scan_count(tracking_id, current_count)
        
        # Update scan progress for the completed scan type
        update_scan_progress(tracking_id, scan_type)
        
        # Save scan record for recent activities
        # Get complete tracker data for the first tracker to populate scan record details
        all_tracker_data = firestore_service.get_all_tracker_data()
        first_tracker_code = trackers[0]['tracker_code'] if trackers else None
        first_tracker_data = all_tracker_data.get(first_tracker_code, {}) if first_tracker_code else {}
        
        scan_record = {
            "tracking_id": tracking_id,
            "scan_type": scan_type,  # Use the actual scan type, not "pending"
            "action": "unhold_complete",
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "platform": first_tracker_data.get('channel_name', 'Unknown'),
            "amount": first_tracker_data.get('amount', 0),
            "buyer_city": first_tracker_data.get('buyer_city', 'Unknown'),
            "courier": first_tracker_data.get('courier', 'Unknown'),
            "distribution": "Single SKU" if len(trackers) == 1 else "Multi SKU",
            "scan_status": "Success"
        }
        firestore_service.save_scan(scan_record)
        
        return {
            "message": f"Shipment for tracking ID {tracking_id} has been unhold and {scan_type} scan completed.",
            "tracking_id": tracking_id,
            "scan_type": scan_type,
            "unhold_count": unhold_count,
            "completed_scan": scan_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/shipments/pending/")
async def get_pending_shipments(scan_type: str = None):
    """Get all pending shipments with optional scan type filter"""
    try:
        all_tracker_data = firestore_service.get_all_tracker_data()
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        pending_shipments = []
        
        for tracker_code, tracker_data in all_tracker_data.items():
            tracker_status = all_tracker_status.get(tracker_code, {})
            
            if tracker_status.get("pending", False):
                # Determine hold stage based on completed scans
                label_done = tracker_status.get("label", False)
                packing_done = tracker_status.get("packing", False)
                dispatch_done = tracker_status.get("dispatch", False)
                
                # Determine hold stage
                if label_done and packing_done and not dispatch_done:
                    hold_stage = "Dispatch Hold"
                elif label_done and not packing_done:
                    hold_stage = "Packing Hold"
                elif not label_done:
                    hold_stage = "Label Hold"
                else:
                    hold_stage = "Unknown Hold"
                
                # If scan_type is specified, only include those
                if scan_type:
                    if scan_type == "packing" and not (label_done and not packing_done):
                        continue
                    elif scan_type == "dispatch" and not (label_done and packing_done and not dispatch_done):
                        continue
                
                # Get hold time from recent scans
                hold_time = "Unknown"
                recent_scans = firestore_service.get_scans_by_type('pending')
                for scan in recent_scans:
                    if scan.get('tracking_id') == tracker_data.get('shipment_tracker', tracker_code):
                        hold_time = scan.get('scan_time', 'Unknown')
                        break
                
                pending_shipments.append({
                    "tracker_code": tracker_code,
                    "tracking_id": tracker_data.get('shipment_tracker', tracker_code),
                    "scan_type": scan_type or "pending",
                    "hold_stage": hold_stage,
                    "hold_time": hold_time,
                    "items_count": 1,  # Default to 1, can be enhanced later
                    "reason": "No reason provided",  # Default reason
                    "details": tracker_data,
                    "status": tracker_status
                })
        
        return {
            "pending_shipments": pending_shipments,
            "count": len(pending_shipments),
            "scan_type": scan_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/shipments/pending/count")
async def get_pending_shipments_count():
    """Get count of pending shipments by scan type"""
    try:
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        packing_pending = 0
        dispatch_pending = 0
        
        for tracker_code, status in all_tracker_status.items():
            if status.get("pending", False):
                if status.get("packing", False):
                    packing_pending += 1
                if status.get("dispatch", False):
                    dispatch_pending += 1
        
        return {
            "packing_pending": packing_pending,
            "dispatch_pending": dispatch_pending,
            "total_pending": packing_pending + dispatch_pending
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/shipments/pending/all")
async def get_all_held_shipments():
    """Get all held shipments with detailed status"""
    try:
        all_tracker_data = firestore_service.get_all_tracker_data()
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        held_shipments = []
        
        for tracker_code, tracker_data in all_tracker_data.items():
            tracker_status = all_tracker_status.get(tracker_code, {})
            
            if tracker_status.get("pending", False):
                # Determine hold type based on completed scans
                label_done = tracker_status.get("label", False)
                packing_done = tracker_status.get("packing", False)
                dispatch_done = tracker_status.get("dispatch", False)
                
                # Determine hold stage
                if label_done and packing_done and not dispatch_done:
                    hold_stage = "Dispatch Hold"
                elif label_done and not packing_done:
                    hold_stage = "Packing Hold"
                elif not label_done:
                    hold_stage = "Label Hold"
                else:
                    hold_stage = "Unknown Hold"
                
                held_shipments.append({
                    "tracker_code": tracker_code,
                    "tracking_id": tracker_data.get('shipment_tracker', tracker_code),
                    "hold_stage": hold_stage,
                    "status": {
                        "label": label_done,
                        "packing": packing_done,
                        "dispatch": dispatch_done,
                        "pending": True
                    },
                    "details": tracker_data,
                    "progress": {
                        "label": "✅ Done" if label_done else "⏳ Pending",
                        "packing": "✅ Done" if packing_done else "⏳ Pending",
                        "dispatch": "✅ Done" if dispatch_done else "⏳ Pending",
                        "hold": "🔴 Hold"
                    }
                })
        
        # Sort by hold stage and tracking ID
        held_shipments.sort(key=lambda x: (x['hold_stage'], x['tracking_id']))
        
        return {
            "held_shipments": held_shipments,
            "count": len(held_shipments),
            "summary": {
                "dispatch_hold": len([s for s in held_shipments if s['hold_stage'] == "Dispatch Hold"]),
                "packing_hold": len([s for s in held_shipments if s['hold_stage'] == "Packing Hold"]),
                "label_hold": len([s for s in held_shipments if s['hold_stage'] == "Label Hold"])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tracker/{tracker_code}/status")
async def get_tracker_status(tracker_code: str):
    """Get status of a specific tracker"""
    try:
        uploaded_trackers = firestore_service.get_uploaded_trackers()
        
        if tracker_code not in uploaded_trackers:
            return {
                "tracker_code": tracker_code,
                "status": "not_uploaded",
                "label": False,
                "packing": False,
                "dispatch": False,
                "pending": False,
                "next_available_scan": "not_available"
            }
        
        status = firestore_service.get_tracker_status(tracker_code)
        if not status:
            return {
                "tracker_code": tracker_code,
                "status": "not_started",
                "label": False,
                "packing": False,
                "dispatch": False,
                "pending": False,
                "next_available_scan": "label"
            }
        
        # Determine overall status
        if status.get("pending", False):
            overall_status = "on_hold"
        elif status.get("label", False) and status.get("packing", False) and status.get("dispatch", False):
            overall_status = "completed"
        elif status.get("label", False) or status.get("packing", False) or status.get("dispatch", False):
            overall_status = "in_progress"
        else:
            overall_status = "not_started"
        
        # Determine next scan
        if status.get("pending", False):
            next_scan = "unhold"
        elif not status.get("label", False):
            next_scan = "label"
        elif not status.get("packing", False):
            next_scan = "packing"
        elif not status.get("dispatch", False):
            next_scan = "dispatch"
        else:
            next_scan = "completed"
        
        # Determine hold stage if on hold
        hold_stage = None
        if status.get("pending", False):
            if status.get("label", False) and status.get("packing", False) and not status.get("dispatch", False):
                hold_stage = "Dispatch Hold"
            elif status.get("label", False) and not status.get("packing", False):
                hold_stage = "Packing Hold"
            elif not status.get("label", False):
                hold_stage = "Label Hold"
            else:
                hold_stage = "Unknown Hold"
        
        return {
            "tracker_code": tracker_code,
            "status": overall_status,
            "label": status.get("label", False),
            "packing": status.get("packing", False),
            "dispatch": status.get("dispatch", False),
            "pending": status.get("pending", False),
            "next_available_scan": next_scan,
            "hold_stage": hold_stage,
            "progress": {
                "label": "✅ Done" if status.get("label", False) else "⏳ Pending",
                "packing": "✅ Done" if status.get("packing", False) else "⏳ Pending",
                "dispatch": "✅ Done" if status.get("dispatch", False) else "⏳ Pending",
                "hold": "🔴 Hold" if status.get("pending", False) else "✅ Active"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tracker/{tracker_code}/packing-details")
async def get_tracker_packing_details(tracker_code: str):
    """Get packing details for a specific tracker"""
    try:
        # Check if tracking ID exists in tracker data
        trackers = get_trackers_by_tracking_id(tracker_code)
        if not trackers:
            raise HTTPException(status_code=404, detail="Tracking ID not found")
        
        # Get the next SKU to scan for packing
        next_sku = get_next_sku_to_scan(tracker_code, "packing")
        if not next_sku:
            raise HTTPException(status_code=400, detail="All SKUs for this tracking ID have been scanned")
        
        # Get progress for this tracking ID
        progress = get_scan_progress(tracker_code, "packing")
        
        return {
            "tracking_id": tracker_code,
            "is_multi_sku": len(trackers) > 1,
            "total_sku_count": len(trackers),
            "scanned_sku_count": progress["scanned"],
            "remaining_sku_count": progress["total"] - progress["scanned"],
            "sku_details": {
                "g_code": next_sku['g_code'],
                "ean_code": next_sku['ean_code'],
                "product_sku_code": next_sku['product_sku_code'],
                "channel_id": next_sku['channel_id']
            },
            "progress": progress
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tracker/{tracking_id}/count")
async def get_tracker_scan_count(tracking_id: str):
    """Get scan count and progress for a tracking ID"""
    try:
        # Check if tracking ID exists in tracker data
        trackers = get_trackers_by_tracking_id(tracking_id)
        if not trackers:
            raise HTTPException(status_code=404, detail="Tracking ID not found")
        
        # Get progress for each scan type
        label_progress = get_scan_progress(tracking_id, "label")
        packing_progress = get_scan_progress(tracking_id, "packing")
        dispatch_progress = get_scan_progress(tracking_id, "dispatch")
        pending_progress = get_scan_progress(tracking_id, "pending")
        
        # Get scan counts
        count_data = firestore_service.get_tracker_scan_count(tracking_id) or {}
        label_count = count_data.get("label", 0)
        packing_count = count_data.get("packing", 0)
        dispatch_count = count_data.get("dispatch", 0)
        pending_count = count_data.get("pending", 0)
        
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
            "pending": {
                "scanned": pending_count,
                "total": len(trackers),
                "progress": pending_progress
            },
            "skus": trackers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/trackers/")
async def get_all_trackers():
    """Get all trackers and their status"""
    try:
        all_status = firestore_service.get_all_tracker_status()
        all_data = firestore_service.get_all_tracker_data()
        
        trackers = []
        # Use all_data keys instead of uploaded_trackers to get the actual document IDs
        for doc_id, tracker_data in all_data.items():
            if doc_id in all_status:
                status = all_status[doc_id]
                next_scan = "label" if not status.get("label", False) else \
                           "packing" if not status.get("packing", False) else \
                           "dispatch" if not status.get("dispatch", False) else "completed"
                
                # Get the original tracking ID from tracker data
                original_tracking_id = tracker_data.get('shipment_tracker', doc_id)
                
                trackers.append({
                    "tracker_code": doc_id,
                    "original_tracking_id": original_tracking_id,
                    "status": status,
                    "next_available_scan": next_scan,
                    "details": tracker_data
                })
            else:
                # Get the original tracking ID from tracker data
                original_tracking_id = tracker_data.get('shipment_tracker', doc_id)
                
                trackers.append({
                    "tracker_code": doc_id,
                    "original_tracking_id": original_tracking_id,
                    "status": {"label": False, "packing": False, "dispatch": False, "pending": False},
                    "next_available_scan": "label",
                    "details": tracker_data
                })
        
        return {"trackers": trackers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    try:
        # Get all data from Firestore
        uploaded_trackers = firestore_service.get_uploaded_trackers()
        all_tracker_data = firestore_service.get_all_tracker_data()
        all_tracker_status = firestore_service.get_all_tracker_status()
        all_scans = firestore_service.get_scans()
        
        # Calculate basic stats
        total_trackers = len(uploaded_trackers)
        total_scans = len(all_scans)
        
        # Count completed trackers
        completed_trackers = 0
        in_progress_trackers = 0
        pending_trackers = 0
        
        for tracker_code in uploaded_trackers:
            tracker_status = all_tracker_status.get(tracker_code, {})
            if tracker_status.get('pending', False):
                pending_trackers += 1
            elif tracker_status.get('label') and tracker_status.get('packing') and tracker_status.get('dispatch'):
                completed_trackers += 1
            elif tracker_status.get('label') or tracker_status.get('packing') or tracker_status.get('dispatch'):
                in_progress_trackers += 1
        
        # Count scan types
        scan_types = {}
        for scan in all_scans:
            scan_type = scan.get('scan_type', 'unknown')
            scan_types[scan_type] = scan_types.get(scan_type, 0) + 1
        
        # Get unique products (by product_sku_code)
        unique_products = set()
        for tracker_code in uploaded_trackers:
            tracker_info = all_tracker_data.get(tracker_code, {})
            product_sku = tracker_info.get('product_sku_code', '')
            if product_sku:
                unique_products.add(product_sku)
        
        total_products = len(unique_products)
        active_products = total_products  # All products are considered active in this context
        
        return {
            "total_products": total_products,
            "active_products": active_products,
            "inactive_products": 0,
            "total_scans": total_scans,
            "total_trackers": total_trackers,
            "completed_trackers": completed_trackers,
            "in_progress_trackers": in_progress_trackers,
            "pending_trackers": pending_trackers,
            "scan_types": scan_types,
            "recent_products": []  # Can be populated later if needed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tracking/stats")
async def get_tracking_statistics():
    """Get comprehensive tracking statistics for dashboard KPIs"""
    try:
        # Get all data from Firestore
        uploaded_trackers = firestore_service.get_uploaded_trackers()
        all_tracker_data = firestore_service.get_all_tracker_data()
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        # Calculate statistics
        total_uploaded = len(uploaded_trackers)
        label_scanned = 0
        packing_scanned = 0
        dispatch_scanned = 0
        completed = 0
        pending = 0
        
        for tracker_code in uploaded_trackers:
            tracker_status = all_tracker_status.get(tracker_code, {})
            
            # Count scan types
            if tracker_status.get('label', False):
                label_scanned += 1
            if tracker_status.get('packing', False):
                packing_scanned += 1
            if tracker_status.get('dispatch', False):
                dispatch_scanned += 1
            if tracker_status.get('pending', False):
                pending += 1
            
            # Count completed (all three scans done)
            if tracker_status.get('label', False) and tracker_status.get('packing', False) and tracker_status.get('dispatch', False):
                completed += 1
        
        # Calculate percentages
        label_percentage = round((label_scanned / total_uploaded * 100) if total_uploaded > 0 else 0, 1)
        packing_percentage = round((packing_scanned / total_uploaded * 100) if total_uploaded > 0 else 0, 1)
        dispatch_percentage = round((dispatch_scanned / total_uploaded * 100) if total_uploaded > 0 else 0, 1)
        completion_percentage = round((completed / total_uploaded * 100) if total_uploaded > 0 else 0, 1)
        pending_percentage = round((pending / total_uploaded * 100) if total_uploaded > 0 else 0, 1)
        
        return {
            "total_uploaded": total_uploaded,
            "label_scanned": label_scanned,
            "packing_scanned": packing_scanned,
            "dispatch_scanned": dispatch_scanned,
            "completed": completed,
            "pending": pending,
            "label_percentage": label_percentage,
            "packing_percentage": packing_percentage,
            "dispatch_percentage": dispatch_percentage,
            "completion_percentage": completion_percentage,
            "pending_percentage": pending_percentage
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/scan/recent")
async def get_recent_scans(page: int = 1, limit: int = 20):
    """Get recent scans with pagination"""
    try:
        all_scans = firestore_service.get_scans()
        
        # Calculate pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        paginated_scans = all_scans[start_idx:end_idx]
        
        return {
            "scans": paginated_scans,
            "page": page,
            "limit": limit,
            "total": len(all_scans),
            "has_next": end_idx < len(all_scans)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/scan/statistics/platform")
async def get_platform_statistics(scan_type: str = None):
    """Get platform/courier statistics with scan counts including Multi-SKU and Single-SKU breakdown"""
    try:
        # Get all data from Firestore
        uploaded_trackers = firestore_service.get_uploaded_trackers()
        all_tracker_data = firestore_service.get_all_tracker_data()
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        # Group trackers by courier and calculate statistics
        courier_stats = {}
        
        # Group trackers by tracking ID to identify Multi-SKU orders
        tracking_id_groups = {}
        for tracker_code in uploaded_trackers:
            tracker_info = all_tracker_data.get(tracker_code, {})
            tracking_id = tracker_info.get('shipment_tracker', '')
            if tracking_id:
                if tracking_id not in tracking_id_groups:
                    tracking_id_groups[tracking_id] = []
                tracking_id_groups[tracking_id].append(tracker_code)
        
        for tracker_code in uploaded_trackers:
            tracker_info = all_tracker_data.get(tracker_code, {})
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
            tracker_status_info = all_tracker_status.get(tracker_code, {})
            
            if scan_type:
                # Filter by specific scan type
                if scan_type == "label":
                    has_scans = tracker_status_info.get("label", False)
                elif scan_type == "packing":
                    has_scans = tracker_status_info.get("packing", False)
                elif scan_type == "dispatch":
                    has_scans = tracker_status_info.get("dispatch", False)
                elif scan_type == "pending":
                    has_scans = tracker_status_info.get("pending", False)
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

@app.get("/api/v1/tracking/progress/{tracking_id}")
async def get_tracking_progress(tracking_id: str):
    """Get detailed progress for a specific tracking ID"""
    try:
        # Get all trackers for this tracking ID
        trackers = get_trackers_by_tracking_id(tracking_id)
        if not trackers:
            raise HTTPException(status_code=404, detail="Tracking ID not found")
        
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        # Calculate progress for each scan type
        label_scanned = 0
        packing_scanned = 0
        dispatch_scanned = 0
        pending_scanned = 0
        total_skus = len(trackers)
        
        for tracker in trackers:
            tracker_code = tracker['tracker_code']
            tracker_status = all_tracker_status.get(tracker_code, {})
            
            if tracker_status.get('label', False):
                label_scanned += 1
            if tracker_status.get('packing', False):
                packing_scanned += 1
            if tracker_status.get('dispatch', False):
                dispatch_scanned += 1
            if tracker_status.get('pending', False):
                pending_scanned += 1
        
        # Calculate percentages
        label_percentage = round((label_scanned / total_skus * 100) if total_skus > 0 else 0, 1)
        packing_percentage = round((packing_scanned / total_skus * 100) if total_skus > 0 else 0, 1)
        dispatch_percentage = round((dispatch_scanned / total_skus * 100) if total_skus > 0 else 0, 1)
        pending_percentage = round((pending_scanned / total_skus * 100) if total_skus > 0 else 0, 1)
        
        # Determine completion status
        is_completed = label_scanned == total_skus and packing_scanned == total_skus and dispatch_scanned == total_skus and pending_scanned == total_skus
        
        return {
            "tracking_id": tracking_id,
            "total_skus": total_skus,
            "label_scanned": label_scanned,
            "packing_scanned": packing_scanned,
            "dispatch_scanned": dispatch_scanned,
            "pending_scanned": pending_scanned,
            "label_percentage": label_percentage,
            "packing_percentage": packing_percentage,
            "dispatch_percentage": dispatch_percentage,
            "pending_percentage": pending_percentage,
            "is_completed": is_completed,
            "next_step": "completed" if is_completed else "label" if label_scanned < total_skus else "packing" if packing_scanned < total_skus else "dispatch" if dispatch_scanned < total_skus else "pending"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/scan/recent/label")
async def get_recent_label_scans(page: int = 1, limit: int = 20):
    """Get recent label scans with pagination"""
    try:
        # Filter scans for label type only
        label_scans = firestore_service.get_scans_by_type('label')
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get recent label scans with tracker details
        recent_scans = []
        all_tracker_data = firestore_service.get_all_tracker_data()
        uploaded_trackers = firestore_service.get_uploaded_trackers()
        
        for scan in label_scans[offset:offset + limit]:
            # Get tracker_code from scan data, fallback to tracking_id if not available
            tracker_code = scan.get('tracker_code', scan.get('tracking_id', ''))
            tracker_info = all_tracker_data.get(tracker_code, {})
            
            # Determine scan status
            scan_status = "Success" if scan.get('status', '') == 'completed' else "Error"
            
            # Determine distribution type
            tracking_id = tracker_info.get('shipment_tracker', tracker_code)
            trackers_with_same_id = [t for t in uploaded_trackers if all_tracker_data.get(t, {}).get('shipment_tracker') == tracking_id]
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
                "tracking_id": tracking_id,
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
        packing_scans = firestore_service.get_scans_by_type('packing')
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get recent packing scans with tracker details
        recent_scans = []
        all_tracker_data = firestore_service.get_all_tracker_data()
        uploaded_trackers = firestore_service.get_uploaded_trackers()
        
        for scan in packing_scans[offset:offset + limit]:
            # Get tracker_code from scan data, fallback to tracking_id if not available
            tracker_code = scan.get('tracker_code', scan.get('tracking_id', ''))
            tracker_info = all_tracker_data.get(tracker_code, {})
            
            # Determine scan status
            scan_status = "Success" if scan.get('status', '') == 'completed' else "Error"
            
            # Determine distribution type
            tracking_id = tracker_info.get('shipment_tracker', tracker_code)
            trackers_with_same_id = [t for t in uploaded_trackers if all_tracker_data.get(t, {}).get('shipment_tracker') == tracking_id]
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
                "tracking_id": tracking_id,
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
        dispatch_scans = firestore_service.get_scans_by_type('dispatch')
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get recent dispatch scans with tracker details
        recent_scans = []
        all_tracker_data = firestore_service.get_all_tracker_data()
        uploaded_trackers = firestore_service.get_uploaded_trackers()
        
        for scan in dispatch_scans[offset:offset + limit]:
            # Get tracker_code from scan data, fallback to tracking_id if not available
            tracker_code = scan.get('tracker_code', scan.get('tracking_id', ''))
            tracker_info = all_tracker_data.get(tracker_code, {})
            
            # Determine scan status - check multiple possible fields
            scan_status = "Error"
            if scan.get('status', '') == 'completed' or scan.get('scan_status', '') == 'Success':
                scan_status = "Success"
            
            # Determine distribution type
            tracking_id = tracker_info.get('shipment_tracker', tracker_code)
            trackers_with_same_id = [t for t in uploaded_trackers if all_tracker_data.get(t, {}).get('shipment_tracker') == tracking_id]
            distribution = "Multi SKU" if len(trackers_with_same_id) > 1 else "Single SKU"
            
            # Format scan time - try multiple possible fields
            scan_time = scan.get('scan_time', scan.get('timestamp', ''))
            if scan_time:
                try:
                    # Handle different timestamp formats
                    if 'T' in scan_time:
                        dt = datetime.fromisoformat(scan_time.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(scan_time, "%Y-%m-%d %H:%M:%S")
                    scan_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    # If parsing fails, use the original value
                    scan_time = scan_time
            else:
                scan_time = "Unknown"
            
            recent_scans.append({
                "id": str(scan.get('id', '')),
                "tracking_id": tracking_id,
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

@app.post("/api/v1/system/clear-data/")
async def clear_all_data():
    """Clear all data from Firestore except pending shipments"""
    try:
        # Get all tracker status to identify pending shipments
        all_tracker_status = firestore_service.get_all_tracker_status()
        pending_trackers = []
        
        # Identify trackers that are on pending status
        for tracker_code, status in all_tracker_status.items():
            if status.get("pending", False):
                pending_trackers.append(tracker_code)
        
        # Clear all data except pending shipments
        firestore_service.clear_all_data_except_pending(pending_trackers)
        
        return {
            "message": f"All data cleared successfully. {len(pending_trackers)} pending shipments preserved.",
            "preserved_pending_count": len(pending_trackers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/system/migrate-from-json/")
async def migrate_from_json():
    """Migrate data from JSON file to Firestore"""
    try:
        firestore_service.migrate_from_json()
        return {"message": "Data migration completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/system/fix-data-inconsistency/")
async def fix_data_inconsistency():
    """Fix data inconsistency where packing scans exist without label scans"""
    try:
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        fixed_count = 0
        
        for tracker_code, status in all_tracker_status.items():
            # Check if packing is completed but label is not
            if status.get("packing", False) and not status.get("label", False):
                # Fix the inconsistency by setting packing to False
                status["packing"] = False
                sanitized_tracker_code = get_sanitized_tracker_code(tracker_code)
                firestore_service.save_tracker_status(sanitized_tracker_code, status)
                fixed_count += 1
                
                print(f"Fixed inconsistency for tracker {tracker_code}: packing reset to False")
        
        return {
            "message": f"Data inconsistency fixed. {fixed_count} trackers updated.",
            "fixed_count": fixed_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/system/migrate-to-unique-ids/")
async def migrate_to_unique_ids():
    """Migrate existing data to use unique document IDs"""
    try:
        all_tracker_data = firestore_service.get_all_tracker_data()
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        migrated_count = 0
        
        for old_doc_id, tracker_data in all_tracker_data.items():
            # Skip if already has unique ID format (contains timestamp)
            if '_' in old_doc_id and len(old_doc_id.split('_')) >= 3:
                continue
                
            # Generate new unique document ID
            import time
            timestamp = int(time.time() * 1000)  # milliseconds
            random_suffix = str(uuid.uuid4())[:8]  # 8 characters from UUID
            new_doc_id = f"{sanitize_tracker_code(old_doc_id)}_{timestamp}_{random_suffix}"
            
            # Save data with new document ID
            firestore_service.save_tracker_data(new_doc_id, tracker_data)
            
            # Migrate status if exists
            if old_doc_id in all_tracker_status:
                status = all_tracker_status[old_doc_id]
                firestore_service.save_tracker_status(new_doc_id, status)
            
            # Delete old document
            firestore_service.delete_tracker_data(old_doc_id)
            
            # Delete old status
            firestore_service.delete_tracker_status(old_doc_id)
            
            migrated_count += 1
            print(f"Migrated tracker {old_doc_id} to {new_doc_id}")
        
        return {
            "message": f"Migration completed. {migrated_count} trackers migrated to unique IDs.",
            "migrated_count": migrated_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/scans/recent/")
async def get_recent_scans(
    scan_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    """Get recent scans with optional filtering by scan type"""
    try:
        all_scans = firestore_service.get_scans()
        
        # Filter by scan type if specified
        if scan_type:
            filtered_scans = [scan for scan in all_scans if scan.get('scan_type') == scan_type]
        else:
            filtered_scans = all_scans
        
        # Sort by scan time (most recent first)
        def get_scan_time(scan):
            # Try different timestamp fields
            scan_time = scan.get('scan_time', scan.get('timestamp', ''))
            if scan_time:
                try:
                    if 'T' in scan_time:
                        dt = datetime.fromisoformat(scan_time.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(scan_time, "%Y-%m-%d %H:%M:%S")
                    return dt
                except:
                    return datetime.min
            return datetime.min
        
        filtered_scans.sort(key=get_scan_time, reverse=True)
        
        # Calculate pagination
        total_count = len(filtered_scans)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paginated_scans = filtered_scans[start_index:end_index]
        
        # Get tracker data for enrichment
        all_tracker_data = firestore_service.get_all_tracker_data()
        uploaded_trackers = firestore_service.get_uploaded_trackers()
        
        # Create a mapping from tracker_code to tracker data
        tracker_code_to_data = {}
        for doc_id, data in all_tracker_data.items():
            # Map by document ID
            tracker_code_to_data[doc_id] = data
            # Map by tracker_code field if it exists
            if 'tracker_code' in data:
                tracker_code_to_data[data['tracker_code']] = data
            # Map by shipment_tracker for backward compatibility
            if 'shipment_tracker' in data:
                tracker_code_to_data[data['shipment_tracker']] = data
            # Also map by the original tracking ID for scans that might use it
            if 'tracking_id' in data:
                tracker_code_to_data[data['tracking_id']] = data
        
        # Format results
        results = []
        for scan in paginated_scans:
            # Get tracker_code from scan data
            tracker_code = scan.get('tracker_code', scan.get('tracking_id', ''))
            tracker_info = tracker_code_to_data.get(tracker_code, {})
            

            
            # Determine scan status
            scan_status = "Unknown"
            if scan.get('status', '') == 'completed' or scan.get('scan_status', '') == 'Success':
                scan_status = "Success"
            elif scan.get('scan_status', '') == 'Error':
                scan_status = "Error"
            
            # Determine distribution type
            tracking_id = tracker_info.get('shipment_tracker', tracker_code)
            trackers_with_same_id = [t for t in uploaded_trackers if all_tracker_data.get(t, {}).get('shipment_tracker') == tracking_id]
            distribution = "Multi SKU" if len(trackers_with_same_id) > 1 else "Single SKU"
            
            # Format scan time
            scan_time = scan.get('scan_time', scan.get('timestamp', ''))
            if scan_time:
                try:
                    if 'T' in scan_time:
                        dt = datetime.fromisoformat(scan_time.replace('Z', '+00:00'))
                        scan_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        scan_time = scan_time
                except:
                    scan_time = scan_time
            
            # For pending scans, show more detailed information
            if scan.get('scan_type') == 'pending':
                hold_stage = scan.get('hold_stage', 'Unknown')
                action = scan.get('action', 'hold')
                items_count = scan.get('items_count', 1)
                reason = scan.get('reason', '')
                
                result = {
                    "id": scan.get('id', ''),
                    "tracking_id": tracking_id,
                    "platform": tracker_info.get('channel_name', 'Unknown'),
                    "last_scan": f"Pending ({hold_stage.title()})",
                    "scan_status": scan_status,
                    "distribution": distribution,
                    "scan_time": scan_time,
                    "amount": tracker_info.get('amount', 0),
                    "buyer_city": tracker_info.get('buyer_city', 'Unknown'),
                    "courier": tracker_info.get('courier', 'Unknown'),
                    "action": action,
                    "hold_stage": hold_stage,
                    "items_count": items_count,
                    "reason": reason,
                    "current_status": "On Hold" if action == "hold" else "Unhold Complete"
                }
            else:
                result = {
                    "id": scan.get('id', ''),
                    "tracking_id": tracking_id,
                    "platform": tracker_info.get('channel_name', 'Unknown'),
                    "last_scan": scan.get('scan_type', '').title(),
                    "scan_status": scan_status,
                    "distribution": distribution,
                    "scan_time": scan_time,
                    "amount": tracker_info.get('amount', 0),
                    "buyer_city": tracker_info.get('buyer_city', 'Unknown'),
                    "courier": tracker_info.get('courier', 'Unknown')
                }
            
            results.append(result)
        

        
        return {
            "results": results,
            "count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/debug/pending-scans")
async def debug_pending_scans():
    """Debug endpoint to see pending scan data"""
    try:
        all_scans = firestore_service.get_scans()
        pending_scans = [scan for scan in all_scans if scan.get('scan_type') == 'pending']
        
        return {
            "total_scans": len(all_scans),
            "pending_scans_count": len(pending_scans),
            "pending_scans": pending_scans[:10]  # Show first 10
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/debug/recent-scans")
async def debug_recent_scans():
    """Debug endpoint to see recent scan data and tracker mapping"""
    try:
        all_scans = firestore_service.get_scans()
        all_tracker_data = firestore_service.get_all_tracker_data()
        
        # Get first 5 scans
        recent_scans = all_scans[:5] if all_scans else []
        
        # Create mapping
        tracker_code_to_data = {}
        for doc_id, data in all_tracker_data.items():
            tracker_code_to_data[doc_id] = data
            if 'tracker_code' in data:
                tracker_code_to_data[data['tracker_code']] = data
            if 'shipment_tracker' in data:
                tracker_code_to_data[data['shipment_tracker']] = data
        
        # Test mapping for each scan
        mapping_results = []
        for scan in recent_scans:
            tracker_code = scan.get('tracker_code', scan.get('tracking_id', ''))
            tracker_info = tracker_code_to_data.get(tracker_code, {})
            
            mapping_results.append({
                "scan_id": scan.get('id'),
                "tracker_code": tracker_code,
                "tracking_id": scan.get('tracking_id'),
                "scan_type": scan.get('scan_type'),
                "found_tracker_info": bool(tracker_info),
                "tracker_info_keys": list(tracker_info.keys()) if tracker_info else [],
                "available_keys": list(tracker_code_to_data.keys())[:5]
            })
        
        return {
            "total_scans": len(all_scans),
            "total_trackers": len(all_tracker_data),
            "recent_scans": recent_scans,
            "mapping_results": mapping_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/shipments/cancelled/")
async def get_cancelled_shipments(scan_type: str = None):
    """Get all cancelled shipments with optional scan type filter"""
    try:
        all_tracker_data = firestore_service.get_all_tracker_data()
        all_tracker_status = firestore_service.get_all_tracker_status()
        
        cancelled_shipments = []
        
        for tracker_code, tracker_data in all_tracker_data.items():
            # Use sanitized tracker code to look up status (same as other endpoints)
            sanitized_tracker_code = get_sanitized_tracker_code(tracker_code)
            tracker_status = all_tracker_status.get(sanitized_tracker_code, {})
            
            if tracker_status.get("cancelled", False):
                # Determine cancellation stage based on completed scans
                label_done = tracker_status.get("label", False)
                packing_done = tracker_status.get("packing", False)
                dispatch_done = tracker_status.get("dispatch", False)
                
                # Determine cancellation stage - show the transition
                if dispatch_done:
                    cancellation_stage = "Post-Dispatch Cancelled"
                elif packing_done:
                    cancellation_stage = "Post-Packing Cancelled"
                elif label_done:
                    cancellation_stage = "Post-Label Cancelled"
                else:
                    cancellation_stage = "Pre-Processing Cancelled"
                
                # If scan_type is specified, only include those
                if scan_type:
                    if scan_type == "packing" and not (label_done and not dispatch_done):
                        continue
                    elif scan_type == "dispatch" and not (label_done and packing_done):
                        continue
                
                # Get cancellation time from recent scans
                cancellation_time = "Unknown"
                recent_scans = firestore_service.get_scans_by_type('cancelled')
                for scan in recent_scans:
                    if scan.get('tracking_id') == tracker_data.get('shipment_tracker', tracker_code):
                        cancellation_time = scan.get('scan_time', 'Unknown')
                        break
                
                cancelled_shipments.append({
                    "tracker_code": tracker_code,
                    "tracking_id": tracker_data.get('shipment_tracker', tracker_code),
                    "scan_type": scan_type or "cancelled",
                    "cancellation_stage": cancellation_stage,
                    "cancellation_time": cancellation_time,
                    "items_count": 1,  # Default to 1, can be enhanced later
                    "reason": "Shipment cancelled",  # Default reason
                    "details": tracker_data,
                    "status": tracker_status
                })
        
        return {
            "cancelled_shipments": cancelled_shipments,
            "count": len(cancelled_shipments),
            "scan_type": scan_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/shipments/cancelled/count")
async def get_cancelled_shipments_count():
    """Get count of cancelled shipments by scan type"""
    try:
        all_tracker_status = firestore_service.get_all_tracker_status()
        all_tracker_data = firestore_service.get_all_tracker_data()
        
        packing_cancelled = 0
        dispatch_cancelled = 0
        
        for tracker_code, tracker_data in all_tracker_data.items():
            # Use sanitized tracker code to look up status
            sanitized_tracker_code = get_sanitized_tracker_code(tracker_code)
            status = all_tracker_status.get(sanitized_tracker_code, {})
            
            if status.get("cancelled", False):
                if status.get("packing", False) and not status.get("dispatch", False):
                    packing_cancelled += 1
                if status.get("dispatch", False):
                    dispatch_cancelled += 1
        
        return {
            "packing_cancelled": packing_cancelled,
            "dispatch_cancelled": dispatch_cancelled,
            "total_cancelled": packing_cancelled + dispatch_cancelled
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("Using Firestore database - No local file storage")
    uvicorn.run(app, host="0.0.0.0", port=8000) 