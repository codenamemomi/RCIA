from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from core.config import settings
from typing import Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

# Create the FastMCP Server
# instructions help the LLM understand how to use this agent
mcp = FastMCP(
    "RCIA-Agent",
    instructions="I am the Research & Compliance Infrastructure for Agents (RCIA). I provide tools to check agent status, trade history, and trigger market evaluations.",
    mount_path="/api/v1/mcp",
    message_path="/messages",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=settings.MCP_ENABLE_SECURITY,
        allowed_hosts=[f"{h}:*" for h in settings.MCP_ALLOWED_HOSTS] + settings.MCP_ALLOWED_HOSTS,
        allowed_origins=[f"http://{h}:*" for h in settings.MCP_ALLOWED_HOSTS] + [f"http://{h}" for h in settings.MCP_ALLOWED_HOSTS]
    )
)

# We'll use a globally accessible app reference to get services
app_instance: Optional[Any] = None

def get_app():
    if app_instance is None:
        raise RuntimeError("App instance not initialized in mcp router")
    return app_instance

@mcp.tool()
async def get_agent_status() -> str:
    """Get the current status, metrics, and risk exposure of the RCIA agent."""
    app = get_app()
    from core.config import settings
    
    sm = app.state.state_machine
    ts = app.state.trading_service
    
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
    return json.dumps(status, indent=2)

@mcp.tool()
async def get_trade_history() -> str:
    """Get the history of recent trades executed by the agent."""
    app = get_app()
    ts = app.state.trading_service
    return json.dumps(ts.trade_history, indent=2)

@mcp.tool()
async def trigger_market_evaluation(symbol: str = "BTC/USDT") -> str:
    """Trigger a manual market evaluation and state transition check."""
    app = get_app()
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
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_reputation() -> str:
    """Fetch the agent's current on-chain reputation score."""
    app = get_app()
    trust = app.state.trust_service
    score = await trust.get_reputation()
    result = {"agent_id": trust.agent_id, "trust_score": score}
    return json.dumps(result, indent=2)
