from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductSearch


class ProductService:
    
    @staticmethod
    def create_product(db: Session, product_data: ProductCreate) -> Product:
        """Create a new product"""
        db_product = Product(**product_data.dict())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product
    
    @staticmethod
    def get_product(db: Session, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        return db.query(Product).filter(Product.id == product_id).first()
    
    @staticmethod
    def get_product_by_g_code(db: Session, g_code: str) -> Optional[Product]:
        """Get product by G-code"""
        return db.query(Product).filter(Product.g_code == g_code).first()
    
    @staticmethod
    def get_product_by_ean_code(db: Session, ean_code: str) -> Optional[Product]:
        """Get product by EAN code"""
        return db.query(Product).filter(Product.ean_code == ean_code).first()
    
    @staticmethod
    def get_products(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[ProductSearch] = None
    ) -> List[Product]:
        """Get products with optional search filters"""
        query = db.query(Product)
        
        if search:
            filters = []
            if search.g_code:
                filters.append(Product.g_code.ilike(f"%{search.g_code}%"))
            if search.ean_code:
                filters.append(Product.ean_code.ilike(f"%{search.ean_code}%"))
            if search.name:
                filters.append(Product.name.ilike(f"%{search.name}%"))
            if search.category:
                filters.append(Product.category.ilike(f"%{search.category}%"))
            if search.brand:
                filters.append(Product.brand.ilike(f"%{search.brand}%"))
            if search.is_active is not None:
                filters.append(Product.is_active == search.is_active)
            
            if filters:
                query = query.filter(and_(*filters))
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def count_products(db: Session, search: Optional[ProductSearch] = None) -> int:
        """Count total products with optional search filters"""
        query = db.query(Product)
        
        if search:
            filters = []
            if search.g_code:
                filters.append(Product.g_code.ilike(f"%{search.g_code}%"))
            if search.ean_code:
                filters.append(Product.ean_code.ilike(f"%{search.ean_code}%"))
            if search.name:
                filters.append(Product.name.ilike(f"%{search.name}%"))
            if search.category:
                filters.append(Product.category.ilike(f"%{search.category}%"))
            if search.brand:
                filters.append(Product.brand.ilike(f"%{search.brand}%"))
            if search.is_active is not None:
                filters.append(Product.is_active == search.is_active)
            
            if filters:
                query = query.filter(and_(*filters))
        
        return query.count()
    
    @staticmethod
    def update_product(db: Session, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
        """Update product"""
        db_product = ProductService.get_product(db, product_id)
        if not db_product:
            return None
        
        update_data = product_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_product, field, value)
        
        db.commit()
        db.refresh(db_product)
        return db_product
    
    @staticmethod
    def delete_product(db: Session, product_id: int) -> bool:
        """Delete product"""
        db_product = ProductService.get_product(db, product_id)
        if not db_product:
            return False
        
        db.delete(db_product)
        db.commit()
        return True
    
    @staticmethod
    def search_products(db: Session, search_term: str) -> List[Product]:
        """Search products by G-code, EAN code, or name"""
        return db.query(Product).filter(
            or_(
                Product.g_code.ilike(f"%{search_term}%"),
                Product.ean_code.ilike(f"%{search_term}%"),
                Product.name.ilike(f"%{search_term}%"),
                Product.product_sku_code.ilike(f"%{search_term}%")
            )
        ).all()
    
    @staticmethod
    def get_active_products(db: Session) -> List[Product]:
        """Get all active products"""
        return db.query(Product).filter(Product.is_active == 1).all()
    
    @staticmethod
    def validate_product_codes(db: Session, g_code: str, ean_code: str) -> Dict[str, Any]:
        """Validate if product codes exist and are unique"""
        result = {
            "is_valid": True,
            "errors": [],
            "product": None
        }
        
        # Check if G-code exists
        existing_g_code = db.query(Product).filter(Product.g_code == g_code).first()
        if existing_g_code:
            result["product"] = existing_g_code.to_dict()
        
        # Check if EAN code exists
        existing_ean_code = db.query(Product).filter(Product.ean_code == ean_code).first()
        if existing_ean_code and existing_ean_code.g_code != g_code:
            result["errors"].append(f"EAN code {ean_code} already exists for product {existing_ean_code.g_code}")
            result["is_valid"] = False
        
        return result 