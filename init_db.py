#!/usr/bin/env python3
"""
Database initialization script for Fulfillment Tracking System
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.core.database import create_tables, engine
from app.models import product, order, scan as scan_models
from sqlalchemy import text


def init_database():
    """Initialize the database with tables"""
    print("Initializing database...")
    
    # Create all tables
    create_tables()
    print("✅ Database tables created successfully")
    
    # Test database connection
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    print("✅ Database initialization completed")
    return True


if __name__ == "__main__":
    success = init_database()
    if success:
        print("\n🎉 Database is ready!")
        print("You can now start the application with:")
        print("  uvicorn app.main:app --reload")
    else:
        print("\n❌ Database initialization failed")
        sys.exit(1) 