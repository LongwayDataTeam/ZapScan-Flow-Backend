from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from datetime import datetime
import os
import tempfile
import pandas as pd
from app.services.google_sheets_service import GoogleSheetsService
from app.schemas.workflow import (
    WorkflowUploadResponse, WorkflowProcessResponse, 
    WorkflowClearResponse, WorkflowStatusResponse
)

router = APIRouter()
sheets_service = GoogleSheetsService()


@router.post("/upload", response_model=WorkflowUploadResponse)
async def upload_data_to_sheets(
    file: UploadFile = File(...)
):
    """Upload data directly to Scan Processor tab (max 10MB)"""
    try:
        # Check file size (10MB limit)
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=413, 
                detail="File size exceeds 10MB limit"
            )
        
        # Check file extension
        allowed_extensions = {'.csv', '.xlsx', '.xls', '.txt'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save file temporarily
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file_path = os.path.join(temp_dir, f"workflow_{timestamp}_{file.filename}")
        
        with open(temp_file_path, "wb") as f:
            f.write(content)
        
        # Read and process file
        orders_data = []
        try:
            if file_extension == '.csv':
                df = pd.read_csv(temp_file_path)
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(temp_file_path)
            else:  # .txt
                df = pd.read_csv(temp_file_path, sep='\t')
            
            # Convert DataFrame to list of dictionaries
            orders_data = df.to_dict('records')
            
            # Add IDs and timestamps
            for i, order in enumerate(orders_data):
                order['id'] = i + 1
                order['created_at'] = datetime.now().isoformat()
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        
        # Upload to Scan Processor tab
        upload_result = sheets_service.upload_orders_to_sheets(orders_data)
        
        # Clean up temp file
        os.remove(temp_file_path)
        
        if upload_result["success"]:
            return WorkflowUploadResponse(
                success=True,
                message=upload_result["message"],
                file_size_mb=file_size / (1024 * 1024),
                total_orders=len(orders_data),
                processed_orders=len(orders_data),
                failed_orders=0,
                file_path=temp_file_path
            )
        else:
            raise HTTPException(status_code=500, detail=upload_result["error"])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/process", response_model=WorkflowProcessResponse)
async def process_workflow_in_sheets():
    """Process all workflow data in Scan Processor tab"""
    try:
        # Get current data from Scan Processor tab
        orders_data = sheets_service.get_sheet_data(sheets_service.processor_tab)
        
        if len(orders_data) <= 1:  # Only header or empty
            return WorkflowProcessResponse(
                success=True,
                message="No data to process",
                total_orders=0,
                pending_orders=0,
                orders_with_scans=0,
                total_scans=0,
                scan_breakdown={}
            )
        
        # Convert sheet data to dictionary format
        headers = orders_data[0]
        orders_dict = []
        for row in orders_data[1:]:  # Skip header
            order = {}
            for i, value in enumerate(row):
                if i < len(headers):
                    order[headers[i]] = value
            orders_dict.append(order)
        
        # Process workflow
        process_result = sheets_service.process_workflow_data(orders_dict)
        
        if process_result["success"]:
            return WorkflowProcessResponse(
                success=True,
                message="Workflow processing completed in Scan Processor tab",
                total_orders=process_result["orders_processed"],
                pending_orders=0,
                orders_with_scans=process_result["orders_processed"],
                total_scans=process_result["scans_processed"],
                scan_breakdown={
                    "label": process_result["scans_processed"] // 3,
                    "packing": process_result["scans_processed"] // 3,
                    "dispatch": process_result["scans_processed"] // 3
                }
            )
        else:
            raise HTTPException(status_code=500, detail=process_result["error"])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/clear", response_model=WorkflowClearResponse)
async def clear_and_move_to_database():
    """Move data from Scan Processor to Database tab"""
    try:
        clear_result = sheets_service.clear_and_move_to_database()
        
        if clear_result["success"]:
            return WorkflowClearResponse(
                success=True,
                message=clear_result["message"],
                exported_orders=clear_result["moved_orders"],
                exported_scans=clear_result["moved_scans"],
                cleared_orders=clear_result["moved_orders"],
                cleared_scans=clear_result["moved_scans"],
                google_sheets_url=f"Data moved to {clear_result.get('destination_tab', 'Database')}"
            )
        else:
            raise HTTPException(status_code=500, detail=clear_result["error"])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear operation failed: {str(e)}")


@router.get("/status", response_model=WorkflowStatusResponse)
async def get_sheets_workflow_status():
    """Get current workflow status from Scan Processor tab"""
    try:
        status = sheets_service.get_workflow_status()
        
        return WorkflowStatusResponse(
            total_orders=status["total_orders"],
            total_scans=status["total_scans"],
            scan_progress=status["scan_progress"],
            data_size_mb=status["data_size_mb"],
            can_clear=status["can_clear"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.post("/upload-and-process")
async def upload_and_process_workflow(
    file: UploadFile = File(...)
):
    """Upload data and process workflow in one step"""
    try:
        # First upload
        upload_response = await upload_data_to_sheets(file)
        
        if upload_response.success:
            # Then process
            process_response = await process_workflow_in_sheets()
            
            return {
                "success": True,
                "message": "Upload and process completed",
                "upload": upload_response.dict(),
                "process": process_response.dict()
            }
        else:
            raise HTTPException(status_code=500, detail="Upload failed")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload and process failed: {str(e)}")


@router.get("/sheets-info")
async def get_sheets_info():
    """Get Google Sheets configuration info"""
    try:
        sheets_service = GoogleSheetsService()
        
        return {
            "configured": sheets_service.sheets_service is not None,
            "spreadsheet_id": sheets_service.spreadsheet_id,
            "processor_tab": sheets_service.processor_tab,
            "database_tab": sheets_service.database_tab,
            "available_sheets": [sheets_service.processor_tab, sheets_service.database_tab],
            "message": "Google Sheets API configured" if sheets_service.sheets_service else "Google Sheets not configured"
        }
        
    except Exception as e:
        return {
            "configured": False,
            "error": str(e),
            "message": "Google Sheets setup failed"
        } 