from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ProductBase(BaseModel):
    g_code: str = Field(..., min_length=1, max_length=50, description="Product G-code")
    ean_code: str = Field(..., min_length=1, max_length=20, description="Product EAN code")
    product_sku_code: Optional[str] = Field(None, max_length=100, description="Product SKU code")
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    image_url: Optional[str] = Field(None, max_length=500, description="Product image URL")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    brand: Optional[str] = Field(None, max_length=100, description="Product brand")
    weight: Optional[str] = Field(None, max_length=50, description="Product weight")
    dimensions: Optional[str] = Field(None, max_length=100, description="Product dimensions")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    g_code: Optional[str] = Field(None, min_length=1, max_length=50)
    ean_code: Optional[str] = Field(None, min_length=1, max_length=20)
    product_sku_code: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    weight: Optional[str] = Field(None, max_length=50)
    dimensions: Optional[str] = Field(None, max_length=100)
    is_active: Optional[int] = Field(None, ge=0, le=1)


class ProductResponse(ProductBase):
    id: int
    is_active: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ProductSearch(BaseModel):
    g_code: Optional[str] = None
    ean_code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    is_active: Optional[int] = None


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    size: int
    pages: int 