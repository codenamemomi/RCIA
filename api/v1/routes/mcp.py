from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types
from typing import List, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

# Create the MCP Server
mcp_server = Server("RCIA-Agent")

# We'll use a globally accessible app reference to get services
# This will be initialized in main.py
app_instance: Optional[Any] = None

def get_app():
    if app_instance is None:
        raise RuntimeError("App instance not initialized in mcp router")
    return app_instance

@mcp_server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available RCIA tools."""
    return [
        types.Tool(
            name="get_agent_status",
            description="Get the current status, metrics, and risk exposure of the RCIA agent.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_trade_history",
            description="Get the history of recent trades executed by the agent.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
             name="trigger_market_evaluation",
             description="Trigger a manual market evaluation and state transition check.",
             inputSchema={
                 "type": "object",
                 "properties": {
                     "symbol": {"type": "string", "default": "BTC/USDT"}
                 },
             },
        ),
        types.Tool(
            name="get_reputation",
            description="Fetch the agent's current on-chain reputation score.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: Dict[str, Any] | None
) -> List[types.TextContent]:
    """Handle MCP tool calls by routing to existing services."""
    app = get_app()
    
    try:
        if name == "get_agent_status":
            sm = app.state.state_machine
            ts = app.state.trading_service
            from core.config import settings
            
            metrics = await app.state.market_data.get_market_metrics("BTC/USDT")
            
            status = {
                "agent": {
                    "name": settings.AGENT_NAME,
                    "id": f"#{settings.AGENT_ID}",
                },
                "mode": sm.current_mode,
                "risk": {
                    "current_exposure": ts.risk_service.current_exposure,
                    "daily_pnl": ts.risk_service.daily_pnl,
                    "cumulative_pnl": ts.risk_service.cumulative_pnl,
                    "sharpe_ratio": ts.risk_service.sharpe_ratio,
                },
                "metrics": metrics
            }
            return [types.TextContent(type="text", text=json.dumps(status, indent=2))]

        elif name == "get_trade_history":
            ts = app.state.trading_service
            return [types.TextContent(type="text", text=json.dumps(ts.trade_history, indent=2))]

        elif name == "trigger_market_evaluation":
            symbol = arguments.get("symbol", "BTC/USDT") if arguments else "BTC/USDT"
            md = app.state.market_data
            sm = app.state.state_machine
            
            metrics = await md.get_market_metrics(symbol)
            new_mode, packet = await sm.transition(metrics)
            
            result = {
                "symbol": symbol,
                "new_mode": new_mode,
                "transition_occurred": packet != {},
                "packet": packet
            }
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_reputation":
            trust = app.state.trust_service
            score = await trust.get_reputation()
            result = {"agent_id": trust.agent_id, "trust_score": score}
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"MCP tool {name} failed: {e}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

# Create the router for the main application
router = APIRouter()
sse = SseServerTransport("/api/v1/mcp/messages")

@router.get("/sse")
async def sse_endpoint(request: Request):
    """MCP SSE transport endpoint."""
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

@router.post("/messages")
async def handle_messages(request: Request):
    """MCP message handler."""
    return await sse.handle_post_message(request.scope, request.receive, request._send)
