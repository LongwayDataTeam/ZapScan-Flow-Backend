from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse, ProductSearch, ProductListResponse
)
from app.services.product_service import ProductService

router = APIRouter()


@router.post("/", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    """Create a new product"""
    # Check if G-code already exists
    existing_product = ProductService.get_product_by_g_code(db, product.g_code)
    if existing_product:
        raise HTTPException(status_code=400, detail=f"Product with G-code {product.g_code} already exists")
    
    # Check if EAN code already exists
    existing_ean = ProductService.get_product_by_ean_code(db, product.ean_code)
    if existing_ean:
        raise HTTPException(status_code=400, detail=f"Product with EAN code {product.ean_code} already exists")
    
    return ProductService.create_product(db, product)


@router.get("/", response_model=ProductListResponse)
def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    g_code: Optional[str] = Query(None),
    ean_code: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    is_active: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get products with pagination and search filters"""
    search = ProductSearch(
        g_code=g_code,
        ean_code=ean_code,
        name=name,
        category=category,
        brand=brand,
        is_active=is_active
    )
    
    products = ProductService.get_products(db, skip=skip, limit=limit, search=search)
    total = ProductService.count_products(db, search=search)
    
    return ProductListResponse(
        items=products,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get product by ID"""
    product = ProductService.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db)
):
    """Update product"""
    updated_product = ProductService.update_product(db, product_id, product)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated_product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete product"""
    success = ProductService.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}


@router.get("/search/{search_term}")
def search_products(search_term: str, db: Session = Depends(get_db)):
    """Search products by G-code, EAN code, or name"""
    products = ProductService.search_products(db, search_term)
    return {"products": [product.to_dict() for product in products]}


@router.get("/g-code/{g_code}", response_model=ProductResponse)
def get_product_by_g_code(g_code: str, db: Session = Depends(get_db)):
    """Get product by G-code"""
    product = ProductService.get_product_by_g_code(db, g_code)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/ean-code/{ean_code}", response_model=ProductResponse)
def get_product_by_ean_code(ean_code: str, db: Session = Depends(get_db)):
    """Get product by EAN code"""
    product = ProductService.get_product_by_ean_code(db, ean_code)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/active/list")
def get_active_products(db: Session = Depends(get_db)):
    """Get all active products"""
    products = ProductService.get_active_products(db)
    return {"products": [product.to_dict() for product in products]} 