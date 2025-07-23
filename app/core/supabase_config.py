import os
from typing import Optional
from supabase import create_client, Client
from app.core.config import settings


class SupabaseConfig:
    """Supabase configuration and client management"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.client: Optional[Client] = None
        
        if self.supabase_url and self.supabase_key:
            self.client = create_client(self.supabase_url, self.supabase_key)
    
    def get_client(self) -> Client:
        """Get Supabase client instance"""
        if not self.client:
            raise ValueError("Supabase client not initialized. Check SUPABASE_URL and SUPABASE_ANON_KEY")
        return self.client
    
    def get_database_url(self) -> str:
        """Get PostgreSQL connection URL for SQLAlchemy"""
        if not self.supabase_url:
            return settings.DATABASE_URL
        
        # Extract database connection details from Supabase URL
        # Format: postgresql://postgres:[password]@[host]:[port]/postgres
        password = os.getenv("SUPABASE_DB_PASSWORD")
        host = self.supabase_url.replace("https://", "").replace(".supabase.co", "")
        
        return f"postgresql://postgres:{password}@{host}.supabase.co:5432/postgres"


# Global Supabase instance
supabase_config = SupabaseConfig() 