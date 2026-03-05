from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from api.db.session import async_engine
from api.v1.services.market_data import MarketDataService
from api.v1.services.risk import RiskService
from api.v1.services.trading import TradingService
from api.v1.services.trust import TrustService
from api.v1.services.yield_optimization import YieldService
from api.v1.services.hedge import HedgeService
from core.state_machine import CapitalStateMachine
from api.v1.routes import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Singleton Services
    print("Starting up RCIA API...")
    
    trust = TrustService()
    md = MarketDataService()
    rs = RiskService()
    sm = CapitalStateMachine()
    ys = YieldService(trust)
    hs = HedgeService(trust)
    ts = TradingService(md, rs, trust, sm, ys, hs)
    
    app.state.trust_service = trust
    app.state.market_data = md
    app.state.risk_service = rs
    app.state.trading_service = ts
    app.state.state_machine = sm
    app.state.yield_service = ys
    app.state.hedge_service = hs
    
    yield
    
    # Shutdown
    print("Shutting down RCIA API...")
    await md.close()

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

# Include API router
app.include_router(api_router, prefix="/api/v1")

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
