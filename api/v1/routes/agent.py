from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, List
from core.state_machine import CapitalStateMachine
from api.v1.services.trading import TradingService
from api.v1.services.trust import TrustService
from core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/status")
async def get_status(request: Request):
    """Returns the current state, metrics, and risk exposure of the agent."""
    sm: CapitalStateMachine = request.app.state.state_machine
    ts: TradingService = request.app.state.trading_service
    
    return {
        "agent": {
            "name": settings.AGENT_NAME,
            "id": f"#{settings.AGENT_ID}",
            "owner": settings.AGENT_OWNER_ADDRESS,
            "network": settings.BLOCKCHAIN_NETWORK_NAME,
            "identity_registry": settings.ERC8004_IDENTITY_REGISTRY,
            "smart_account": request.app.state.trust_service.erc4337.get_smart_account_address()
        },
        "mode": sm.current_mode,
        "last_transition": sm.last_transition_time.isoformat() if sm.last_transition_time else None,
        "risk": {
            "current_exposure": ts.risk_service.current_exposure,
            "daily_pnl": ts.risk_service.daily_pnl,
            "cumulative_pnl": ts.risk_service.cumulative_pnl,
            "sharpe_ratio": ts.risk_service.sharpe_ratio,
            "win_rate": ts.risk_service.winning_trades / ts.risk_service.total_trades if ts.risk_service.total_trades > 0 else 0
        },
        "metrics": await request.app.state.market_data.get_market_metrics("BTC/USDT"),
        "history_count": len(request.app.state.trust_service.history)
    }

@router.get("/history")
async def get_trade_history(request: Request):
    """Returns the history of recent trades."""
    ts: TradingService = request.app.state.trading_service
    return ts.trade_history

@router.get("/validation")
async def get_validation_history(request: Request):
    """Returns the history of signed validation artifacts from the trust service."""
    trust = request.app.state.trust_service
    return trust.history

@router.post("/evaluate")
async def trigger_evaluation(request: Request, symbol: str = "BTC/USDT"):
    """Triggers a manual evaluation of market metrics and state transition."""
    md = request.app.state.market_data
    sm = request.app.state.state_machine
    
    try:
        metrics = await md.get_market_metrics(symbol)
        new_mode, packet = await sm.transition(metrics)
        return {
            "symbol": symbol,
            "new_mode": new_mode,
            "transition_occurred": packet != {},
            "packet": packet
        }
    except Exception as e:
        logger.error(f"Manual evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signal")
async def get_signal(request: Request, symbol: str = "BTC/USDT"):
    """Returns the current trading or allocation signal based on the agent mode."""
    ts: TradingService = request.app.state.trading_service
    try:
        signal = await ts.get_trade_signal(symbol)
        return signal
    except Exception as e:
        logger.error(f"Failed to fetch signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reputation")
async def get_reputation(request: Request):
    """Fetches current agent reputation from the trust service."""
    trust: TrustService = request.app.state.trust_service
    score = await trust.get_reputation()
    return {"agent_id": trust.agent_id, "trust_score": score}
