from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    g_code = Column(String(50), unique=True, nullable=False, index=True)
    ean_code = Column(String(20), unique=True, nullable=False, index=True)
    product_sku_code = Column(String(100), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True)
    brand = Column(String(100), nullable=True)
    weight = Column(String(50), nullable=True)
    dimensions = Column(String(100), nullable=True)
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Product(id={self.id}, g_code='{self.g_code}', name='{self.name}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "g_code": self.g_code,
            "ean_code": self.ean_code,
            "product_sku_code": self.product_sku_code,
            "name": self.name,
            "description": self.description,
            "image_url": self.image_url,
            "category": self.category,
            "brand": self.brand,
            "weight": self.weight,
            "dimensions": self.dimensions,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 