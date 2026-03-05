import pytest
import asyncio
from unittest.mock import MagicMock, patch
from api.v1.services.trading import TradingService
from api.v1.services.risk import RiskService
from api.v1.services.trust import TrustService
from api.v1.services.market_data import MarketDataService
from core.state_machine import CapitalStateMachine, AgentMode

@pytest.mark.asyncio
async def test_losing_streak_stability():
    """
    Simulate a losing streak and verify:
    1. Daily PnL tracking
    2. Transition to DEFENSIVE if daily loss limit reached
    """
    # Setup mocks
    mock_md = MagicMock(spec=MarketDataService)
    mock_trust = MagicMock(spec=TrustService)
    mock_trust.agent_id = 1
    mock_trust.emit_validation = MagicMock(return_value=asyncio.Future())
    mock_trust.emit_validation.return_value.set_result({"tx_hash": "0x123", "on_chain_status": "submitted"})
    
    risk = RiskService()
    sm = CapitalStateMachine()
    ts = TradingService(mock_md, risk, mock_trust, sm)

    # Mock market metrics
    metrics = {"volatility": 0.05, "momentum": 0.1, "drawdown": 0.01}
    mock_md.get_market_metrics.return_value = metrics
    
    # 1. Simulate 3 losing trades
    # (Simplified: manually update risk state to simulate losses)
    loss_per_trade = -0.01 # 1% loss
    
    # First 2 trades
    risk.update_state(0.5, loss_per_trade)
    risk.update_state(0.5, loss_per_trade)
    
    assert risk.daily_pnl == -0.02
    
    # 3. Third trade should trigger "Risk limits reached" if limit is 0.02
    # Verify via validate_trade
    is_safe, reason = risk.validate_trade("BTC/USDT", "BUY", 0.1, metrics)
    assert is_safe is False
    assert "Daily loss limit reached" in reason

    # 4. State machine should transition to DEFENSIVE if drawdown increases
    metrics["drawdown"] = 0.06 # Above 0.05 threshold
    new_mode, _ = await sm.transition(metrics)
    assert new_mode == AgentMode.DEFENSIVE

@pytest.mark.asyncio
async def test_rpc_failure_resilience():
    """
    Simulate an RPC failure during trust submission and verify error handling.
    """
    mock_md = MagicMock(spec=MarketDataService)
    mock_trust = TrustService() # Real instance but we will patch w3
    
    # Patch Web3 provider to raise an exception
    with patch.object(mock_trust.w3.eth, 'get_transaction_count', side_effect=Exception("RPC Connection Failed")):
        risk = RiskService()
        sm = CapitalStateMachine()
        ts = TradingService(mock_md, risk, mock_trust, sm)
        
        # Attempt to emit validation should fail gracefully or be handled
        try:
            await mock_trust.emit_validation("TEST", {"data": "test"})
            pytest.fail("Should have raised an RPC error")
        except Exception as e:
            assert "RPC Connection Failed" in str(e)
            
        # In a real app, the calling service (like StateMachine) would catch this
        # and trigger a safety mode. Let's verify our state machine logic doesn't crash.
        # However, currently emit_validation is awaited directly in transitions.
        # A robust implementation would wrap it.
