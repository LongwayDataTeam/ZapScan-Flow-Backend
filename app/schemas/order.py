from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal


class OrderItemBase(BaseModel):
    g_code: str = Field(..., min_length=1, max_length=50, description="Product G-code")
    ean_code: Optional[str] = Field(None, max_length=20, description="Product EAN code")
    product_sku_code: Optional[str] = Field(None, max_length=100, description="Product SKU code")
    quantity: int = Field(..., gt=0, description="Item quantity")
    amount: Optional[Decimal] = Field(None, description="Item amount")


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    product_id: Optional[int]
    item_status: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    channel_id: Optional[str] = Field(None, max_length=50)
    order_id: str = Field(..., min_length=1, max_length=100)
    po_id: Optional[str] = Field(None, max_length=100)
    shipment_number: Optional[str] = Field(None, max_length=100)
    sub_order_id: Optional[str] = Field(None, max_length=100)
    invoice_number: Optional[str] = Field(None, max_length=100)
    shipment_tracker: str = Field(..., min_length=1, max_length=100)
    courier: Optional[str] = Field(None, max_length=100)
    channel_name: Optional[str] = Field(None, max_length=100)
    channel_listing_id: Optional[str] = Field(None, max_length=100)
    total_amount: Optional[Decimal] = None
    payment_mode: Optional[str] = Field(None, max_length=20)
    order_status: Optional[str] = Field(None, max_length=50)
    buyer_city: Optional[str] = Field(None, max_length=100)
    buyer_state: Optional[str] = Field(None, max_length=100)
    buyer_pincode: Optional[str] = Field(None, max_length=10)


class OrderCreate(OrderBase):
    items: List[OrderItemCreate] = Field(..., min_items=1, description="Order items")


class OrderUpdate(BaseModel):
    channel_id: Optional[str] = Field(None, max_length=50)
    order_id: Optional[str] = Field(None, min_length=1, max_length=100)
    po_id: Optional[str] = Field(None, max_length=100)
    shipment_number: Optional[str] = Field(None, max_length=100)
    sub_order_id: Optional[str] = Field(None, max_length=100)
    invoice_number: Optional[str] = Field(None, max_length=100)
    courier: Optional[str] = Field(None, max_length=100)
    channel_name: Optional[str] = Field(None, max_length=100)
    channel_listing_id: Optional[str] = Field(None, max_length=100)
    total_amount: Optional[Decimal] = None
    payment_mode: Optional[str] = Field(None, max_length=20)
    order_status: Optional[str] = Field(None, max_length=50)
    buyer_city: Optional[str] = Field(None, max_length=100)
    buyer_state: Optional[str] = Field(None, max_length=100)
    buyer_pincode: Optional[str] = Field(None, max_length=10)
    fulfillment_status: Optional[str] = Field(None, max_length=20)


class OrderResponse(OrderBase):
    id: int
    order_date: Optional[datetime]
    fulfillment_status: str
    is_multi_sku: bool
    is_multi_quantity: bool
    total_items: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    items: List[OrderItemResponse]
    
    class Config:
        from_attributes = True


class OrderSearch(BaseModel):
    shipment_tracker: Optional[str] = None
    order_id: Optional[str] = None
    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    fulfillment_status: Optional[str] = None
    buyer_city: Optional[str] = None
    buyer_state: Optional[str] = None
    is_multi_sku: Optional[bool] = None
    is_multi_quantity: Optional[bool] = None
    order_date_from: Optional[datetime] = None
    order_date_to: Optional[datetime] = None


class OrderListResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    page: int
    size: int
    pages: int


class OrderUploadResponse(BaseModel):
    total_processed: int
    successful: int
    failed: int
    errors: List[str]
    message: str


class MultiSkuOrderResponse(BaseModel):
    shipment_tracker: str
    total_items: int
    items: List[OrderItemResponse]
    fulfillment_status: str
    is_completed: bool
    scan_progress: dict 