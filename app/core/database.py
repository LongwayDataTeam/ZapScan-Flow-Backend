from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import get_database_url
from app.core.supabase_config import supabase_config

# Create SQLAlchemy engine
def get_engine():
    """Get database engine with Supabase support"""
    database_url = supabase_config.get_database_url() if supabase_config.supabase_url else get_database_url()
    
    return create_engine(
        database_url,
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        pool_pre_ping=True,
        echo=False  # Set to True for SQL query logging
    )

engine = get_engine()

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all tables in the database"""
    Base.metadata.drop_all(bind=engine) 