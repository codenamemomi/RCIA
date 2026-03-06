from fastapi import APIRouter
from api.v1.routes import agent, mcp

api_router = APIRouter()
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
