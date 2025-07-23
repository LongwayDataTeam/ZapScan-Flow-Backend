#!/usr/bin/env python3
"""
Supabase Database Migration Script
Sets up tables and initial data for Fulfillment Tracking System
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.core.supabase_config import supabase_config
from app.models import product, order, scan as scan_models
from sqlalchemy import create_engine, text
from app.core.database import create_tables


def setup_supabase_tables():
    """Create tables in Supabase database"""
    print("Setting up Supabase database tables...")
    
    try:
        # Create tables using SQLAlchemy
        create_tables()
        print("✅ Tables created successfully")
        
        # Test connection
        engine = create_engine(supabase_config.get_database_url())
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


def create_supabase_policies():
    """Create Row Level Security policies for Supabase"""
    print("Setting up Supabase RLS policies...")
    
    try:
        client = supabase_config.get_client()
        
        # Enable RLS on tables
        policies = [
            # Orders table policies
            """
            ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
            CREATE POLICY "Enable read access for all users" ON orders FOR SELECT USING (true);
            CREATE POLICY "Enable insert access for all users" ON orders FOR INSERT WITH CHECK (true);
            CREATE POLICY "Enable update access for all users" ON orders FOR UPDATE USING (true);
            """,
            
            # Order items table policies
            """
            ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
            CREATE POLICY "Enable read access for all users" ON order_items FOR SELECT USING (true);
            CREATE POLICY "Enable insert access for all users" ON order_items FOR INSERT WITH CHECK (true);
            CREATE POLICY "Enable update access for all users" ON order_items FOR UPDATE USING (true);
            """,
            
            # Products table policies
            """
            ALTER TABLE products ENABLE ROW LEVEL SECURITY;
            CREATE POLICY "Enable read access for all users" ON products FOR SELECT USING (true);
            CREATE POLICY "Enable insert access for all users" ON products FOR INSERT WITH CHECK (true);
            CREATE POLICY "Enable update access for all users" ON products FOR UPDATE USING (true);
            """,
            
            # Scan checkpoints table policies
            """
            ALTER TABLE scan_checkpoints ENABLE ROW LEVEL SECURITY;
            CREATE POLICY "Enable read access for all users" ON scan_checkpoints FOR SELECT USING (true);
            CREATE POLICY "Enable insert access for all users" ON scan_checkpoints FOR INSERT WITH CHECK (true);
            CREATE POLICY "Enable update access for all users" ON scan_checkpoints FOR UPDATE USING (true);
            """
        ]
        
        # Execute policies
        for policy in policies:
            client.rpc('exec_sql', {'sql': policy}).execute()
        
        print("✅ RLS policies created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Policy creation failed: {e}")
        return False


def main():
    """Main migration function"""
    print("🚀 Starting Supabase migration...")
    
    # Check if Supabase is configured
    if not supabase_config.supabase_url:
        print("❌ Supabase not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY")
        return False
    
    # Setup tables
    if not setup_supabase_tables():
        return False
    
    # Setup policies
    if not create_supabase_policies():
        return False
    
    print("\n🎉 Supabase migration completed successfully!")
    print("Your Fulfillment Tracking System is ready to use with Supabase!")
    return True


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 