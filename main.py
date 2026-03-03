from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from api.db.session import async_engine
# Placeholder for models and routes
# from api.v1.models.base import Base
# from api.v1.routes import api_version_one

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up RCIA API...")
    
    # Create tables (for development only - remove in production)
    if settings.DEBUG:
        # async with async_engine.begin() as conn:
        #     await conn.run_sync(Base.metadata.create_all)
        pass
    
    yield
    
    # Shutdown
    print("Shutting down RCIA API...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router (Placeholder)
# app.include_router(api_version_one)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
