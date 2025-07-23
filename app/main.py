from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from app.core.config import settings
from app.core.database import create_tables

# Import all models to ensure they are registered with SQLAlchemy
from app.models import product, order, scan as scan_models

# Import API endpoints
try:
    from app.api.v1.endpoints import products, orders, scan
    API_ENDPOINTS_AVAILABLE = True
except ImportError:
    API_ENDPOINTS_AVAILABLE = False
    print("Warning: Some API endpoints may not be available")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting Fulfillment Tracking System...")
    try:
        create_tables()
        print("Database tables created/verified")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
    
    yield
    
    # Shutdown
    print("Shutting down Fulfillment Tracking System...")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A comprehensive web application for internal fulfillment tracking",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url)
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Fulfillment Tracking System API",
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": "development" if settings.DEBUG else "production"
    }


# Include API routers only if available
if API_ENDPOINTS_AVAILABLE:
    app.include_router(
        products.router,
        prefix=f"{settings.API_V1_STR}/products",
        tags=["products"]
    )

    app.include_router(
        orders.router,
        prefix=f"{settings.API_V1_STR}/orders",
        tags=["orders"]
    )

    app.include_router(
        scan.router,
        prefix=f"{settings.API_V1_STR}/scan",
        tags=["scanning"]
    )

# Import and include data export endpoints
try:
    from app.api.v1.endpoints import data_export
    app.include_router(
        data_export.router,
        prefix=f"{settings.API_V1_STR}/export",
        tags=["data-export"]
    )
except ImportError:
    print("Warning: Data export endpoints not available")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    ) 