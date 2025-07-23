from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.data_export_service import DataExportService
from app.schemas.data_export import (
    ExportRequest, ExportResponse, CleanupResponse, DailySummaryResponse
)

router = APIRouter()
export_service = DataExportService()


@router.post("/export/daily", response_model=ExportResponse)
async def export_daily_data(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Export daily scan data to Google Sheets"""
    try:
        export_date = request.date if request.date else datetime.now().date()
        
        # Export data
        result = export_service.export_daily_data_to_sheets(db, export_date)
        
        if result["success"]:
            # Add cleanup to background tasks if requested
            if request.cleanup_after_export:
                background_tasks.add_task(
                    export_service.cleanup_daily_data, db, export_date
                )
            
            return ExportResponse(
                success=True,
                message=f"Data exported successfully for {export_date}",
                records_exported=result["records_exported"],
                file_path=result["file_path"]
            )
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/cleanup/daily", response_model=CleanupResponse)
async def cleanup_daily_data(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """Clean up daily data from database"""
    try:
        cleanup_date = request.date if request.date else datetime.now().date()
        
        # Get summary before cleanup
        summary = export_service.get_daily_summary(db, cleanup_date)
        
        # Perform cleanup
        result = export_service.cleanup_daily_data(db, cleanup_date)
        
        if result["success"]:
            return CleanupResponse(
                success=True,
                message=f"Data cleaned up successfully for {cleanup_date}",
                deleted_orders=result["deleted_orders"],
                deleted_sessions=result["deleted_sessions"],
                summary_before_cleanup=summary
            )
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/summary/daily", response_model=DailySummaryResponse)
async def get_daily_summary(
    target_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get daily summary statistics"""
    try:
        if target_date:
            try:
                export_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            export_date = datetime.now().date()
        
        summary = export_service.get_daily_summary(db, export_date)
        
        return DailySummaryResponse(
            date=summary["date"],
            total_orders=summary["total_orders"],
            total_scans=summary["total_scans"],
            scan_breakdown=summary["scan_breakdown"],
            data_size_mb=summary["data_size_mb"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


@router.post("/export-and-cleanup", response_model=ExportResponse)
async def export_and_cleanup_daily_data(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Export daily data and then cleanup database"""
    try:
        target_date = request.date if request.date else datetime.now().date()
        
        # First export
        export_result = export_service.export_daily_data_to_sheets(db, target_date)
        
        if not export_result["success"]:
            raise HTTPException(status_code=500, detail=export_result["error"])
        
        # Then cleanup in background
        background_tasks.add_task(
            export_service.cleanup_daily_data, db, target_date
        )
        
        return ExportResponse(
            success=True,
            message=f"Data exported and cleanup scheduled for {target_date}",
            records_exported=export_result["records_exported"],
            file_path=export_result["file_path"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export and cleanup failed: {str(e)}")


@router.get("/health/export")
async def check_export_health():
    """Check if Google Sheets export is configured"""
    try:
        # Check if Google Sheets is configured
        if export_service.sheets_service:
            return {
                "status": "healthy",
                "google_sheets": "configured",
                "message": "Export service is ready"
            }
        else:
            return {
                "status": "warning",
                "google_sheets": "not_configured",
                "message": "Google Sheets not configured, will use CSV export"
            }
    except Exception as e:
        return {
            "status": "error",
            "google_sheets": "error",
            "message": f"Export service error: {str(e)}"
        } 