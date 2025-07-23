from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ScanBase(BaseModel):
    shipment_tracker: str = Field(..., min_length=1, max_length=100, description="Shipment tracker code")
    scanned_by: Optional[str] = Field(None, max_length=100, description="User who performed the scan")
    notes: Optional[str] = Field(None, description="Additional notes for the scan")


class LabelScanCreate(ScanBase):
    pass


class PackingScanCreate(ScanBase):
    g_code: str = Field(..., min_length=1, max_length=50, description="Product G-code being scanned")
    quantity_scanned: int = Field(..., gt=0, description="Quantity scanned for this item")


class DispatchScanCreate(ScanBase):
    pass


class ScanResponse(BaseModel):
    id: int
    order_id: int
    checkpoint_type: str
    scan_time: datetime
    scanned_by: Optional[str]
    scan_data: Optional[str]
    status: str
    notes: Optional[str]
    is_completed: bool
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ScanValidationResponse(BaseModel):
    is_valid: bool
    message: str
    product_info: Optional[Dict[str, Any]] = None
    order_info: Optional[Dict[str, Any]] = None


class ScanStatusResponse(BaseModel):
    shipment_tracker: str
    order_id: int
    fulfillment_status: str
    label_scan: Optional[ScanResponse]
    packing_scans: list[ScanResponse]
    dispatch_scan: Optional[ScanResponse]
    is_completed: bool
    progress_percentage: float
    total_items: int
    scanned_items: int


class ScanHistoryResponse(BaseModel):
    shipment_tracker: str
    scans: list[ScanResponse]
    total_scans: int
    successful_scans: int
    failed_scans: int


class ScanSessionCreate(BaseModel):
    checkpoint_type: str = Field(..., description="Type of checkpoint: label, packing, dispatch")
    user_id: Optional[str] = Field(None, max_length=100)


class ScanSessionResponse(BaseModel):
    session_id: str
    user_id: Optional[str]
    checkpoint_type: str
    start_time: datetime
    end_time: Optional[datetime]
    total_scans: int
    successful_scans: int
    failed_scans: int
    is_active: bool
    
    class Config:
        from_attributes = True


class ScanErrorResponse(BaseModel):
    error: str
    message: str
    shipment_tracker: Optional[str] = None
    g_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None 