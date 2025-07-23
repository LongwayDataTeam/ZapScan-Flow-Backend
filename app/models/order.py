from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String(50), nullable=True, index=True)
    order_id = Column(String(100), nullable=False, index=True)
    po_id = Column(String(100), nullable=True)
    shipment_number = Column(String(100), nullable=True)
    sub_order_id = Column(String(100), nullable=True)
    invoice_number = Column(String(100), nullable=True)
    shipment_tracker = Column(String(100), unique=True, nullable=False, index=True)
    tracker_code = Column(String(100), nullable=True, index=True)  # For Multi-SKU orders with same tracking ID
    courier = Column(String(100), nullable=True)
    channel_name = Column(String(100), nullable=True)
    channel_listing_id = Column(String(100), nullable=True)
    total_amount = Column(Numeric(10, 2), nullable=True)
    payment_mode = Column(String(20), nullable=True)
    order_status = Column(String(50), nullable=True)
    buyer_city = Column(String(100), nullable=True)
    buyer_state = Column(String(100), nullable=True)
    buyer_pincode = Column(String(10), nullable=True)
    order_date = Column(DateTime(timezone=True), server_default=func.now())
    fulfillment_status = Column(String(20), default="pending")  # pending, label_printed, packed, dispatched, completed
    is_multi_sku = Column(Boolean, default=False)
    is_multi_quantity = Column(Boolean, default=False)
    total_items = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    scan_checkpoints = relationship("ScanCheckpoint", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order(id={self.id}, shipment_tracker='{self.shipment_tracker}', status='{self.fulfillment_status}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "order_id": self.order_id,
            "po_id": self.po_id,
            "shipment_number": self.shipment_number,
            "sub_order_id": self.sub_order_id,
            "invoice_number": self.invoice_number,
            "shipment_tracker": self.shipment_tracker,
            "tracker_code": self.tracker_code,
            "courier": self.courier,
            "channel_name": self.channel_name,
            "channel_listing_id": self.channel_listing_id,
            "total_amount": float(self.total_amount) if self.total_amount else None,
            "payment_mode": self.payment_mode,
            "order_status": self.order_status,
            "buyer_city": self.buyer_city,
            "buyer_state": self.buyer_state,
            "buyer_pincode": self.buyer_pincode,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "fulfillment_status": self.fulfillment_status,
            "is_multi_sku": self.is_multi_sku,
            "is_multi_quantity": self.is_multi_quantity,
            "total_items": self.total_items,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "items": [item.to_dict() for item in self.items] if self.items else []
        }


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    g_code = Column(String(50), nullable=False, index=True)
    ean_code = Column(String(20), nullable=True)
    product_sku_code = Column(String(100), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    amount = Column(Numeric(10, 2), nullable=True)
    item_status = Column(String(20), default="pending")  # pending, scanned, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, g_code='{self.g_code}', quantity={self.quantity})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "g_code": self.g_code,
            "ean_code": self.ean_code,
            "product_sku_code": self.product_sku_code,
            "quantity": self.quantity,
            "amount": float(self.amount) if self.amount else None,
            "item_status": self.item_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "product": self.product.to_dict() if self.product else None
        } 