"""
Migration script to add tracker_code field to orders table
"""
from sqlalchemy import text
from app.core.database import engine

def upgrade():
    """Add tracker_code column to orders table"""
    with engine.connect() as conn:
        # Add tracker_code column
        conn.execute(text("""
            ALTER TABLE orders 
            ADD COLUMN tracker_code VARCHAR(100);
        """))
        
        # Create index on tracker_code
        conn.execute(text("""
            CREATE INDEX ix_orders_tracker_code ON orders(tracker_code);
        """))
        
        # Update existing orders to set tracker_code = shipment_tracker
        conn.execute(text("""
            UPDATE orders 
            SET tracker_code = shipment_tracker 
            WHERE tracker_code IS NULL;
        """))
        
        conn.commit()

def downgrade():
    """Remove tracker_code column from orders table"""
    with engine.connect() as conn:
        # Drop index
        conn.execute(text("""
            DROP INDEX IF EXISTS ix_orders_tracker_code;
        """))
        
        # Drop column
        conn.execute(text("""
            ALTER TABLE orders 
            DROP COLUMN IF EXISTS tracker_code;
        """))
        
        conn.commit()

if __name__ == "__main__":
    print("Adding tracker_code field to orders table...")
    upgrade()
    print("Migration completed successfully!") 