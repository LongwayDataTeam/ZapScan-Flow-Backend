#!/usr/bin/env python3
"""
Startup script for the Fulfillment Tracking Backend
"""

import uvicorn
import os
from app.core.config import settings

if __name__ == "__main__":
    print("🚀 Starting Fulfillment Tracking Backend...")
    print(f"📊 Environment: {'Development' if settings.DEBUG else 'Production'}")
    print(f"🌐 Host: {settings.API_HOST if hasattr(settings, 'API_HOST') else '0.0.0.0'}")
    print(f"🔌 Port: {settings.API_PORT if hasattr(settings, 'API_PORT') else 8000}")
    print(f"🔒 CORS Origins: {settings.BACKEND_CORS_ORIGINS}")
    print("=" * 50)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
 