from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ScanCheckpoint(Base):
    __tablename__ = "scan_checkpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    checkpoint_type = Column(String(20), nullable=False)  # 'label', 'packing', 'dispatch'
    scan_time = Column(DateTime(timezone=True), server_default=func.now())
    scanned_by = Column(String(100), nullable=True)
    scan_data = Column(Text, nullable=True)  # JSON data for additional scan info
    status = Column(String(20), default="success")  # success, error, pending
    notes = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="scan_checkpoints")
    
    def __repr__(self):
        return f"<ScanCheckpoint(id={self.id}, type='{self.checkpoint_type}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "checkpoint_type": self.checkpoint_type,
            "scan_time": self.scan_time.isoformat() if self.scan_time else None,
            "scanned_by": self.scanned_by,
            "scan_data": self.scan_data,
            "status": self.status,
            "notes": self.notes,
            "is_completed": self.is_completed,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ScanSession(Base):
    __tablename__ = "scan_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False)
    user_id = Column(String(100), nullable=True)
    checkpoint_type = Column(String(20), nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    total_scans = Column(Integer, default=0)
    successful_scans = Column(Integer, default=0)
    failed_scans = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<ScanSession(id={self.id}, session_id='{self.session_id}', type='{self.checkpoint_type}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "checkpoint_type": self.checkpoint_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_scans": self.total_scans,
            "successful_scans": self.successful_scans,
            "failed_scans": self.failed_scans,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 