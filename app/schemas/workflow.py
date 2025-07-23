from typing import Dict, Any, Optional
from pydantic import BaseModel


class WorkflowUploadResponse(BaseModel):
    """Response model for workflow upload"""
    success: bool
    message: str
    file_size_mb: float
    total_orders: int
    processed_orders: int
    failed_orders: int
    file_path: str


class WorkflowProcessResponse(BaseModel):
    """Response model for workflow processing"""
    success: bool
    message: str
    total_orders: int
    pending_orders: int
    orders_with_scans: int
    total_scans: int
    scan_breakdown: Dict[str, int]


class WorkflowClearResponse(BaseModel):
    """Response model for workflow clear operation"""
    success: bool
    message: str
    exported_orders: int
    exported_scans: int
    cleared_orders: int
    cleared_scans: int
    google_sheets_url: str


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status"""
    total_orders: int
    total_scans: int
    scan_progress: Dict[str, Dict[str, Any]]
    data_size_mb: float
    can_clear: bool 