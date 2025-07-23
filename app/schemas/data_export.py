from datetime import date
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ExportRequest(BaseModel):
    """Request model for data export"""
    date: Optional[date] = None
    cleanup_after_export: bool = False


class ExportResponse(BaseModel):
    """Response model for data export"""
    success: bool
    message: str
    records_exported: int
    file_path: str


class CleanupResponse(BaseModel):
    """Response model for data cleanup"""
    success: bool
    message: str
    deleted_orders: int
    deleted_sessions: int
    summary_before_cleanup: Dict[str, Any]


class DailySummaryResponse(BaseModel):
    """Response model for daily summary"""
    date: str
    total_orders: int
    total_scans: int
    scan_breakdown: Dict[str, int]
    data_size_mb: float 