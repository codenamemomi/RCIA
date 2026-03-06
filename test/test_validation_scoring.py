import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from api.v1.services.trading import TradingService
from api.v1.services.risk import RiskService
from api.v1.services.trust import TrustService
from api.v1.services.market_data import MarketDataService
from core.state_machine import CapitalStateMachine, AgentMode


def make_ohlcv_buy_signal():
    """Creates OHLCV data where fast MA (7) > slow MA (25) to trigger a BUY."""
    # 26 candles: first 19 at 100, last 7 at 200 -> fast_ma=200, slow_ma~138
    ohlcv_data = [[0, 0, 0, 0, 100.0, 0]] * 19 + [[0, 0, 0, 0, 200.0, 0]] * 7
    return ohlcv_data


@pytest.mark.asyncio
async def test_validation_artifact_flow():
    """
    Verifies that all critical events produce the correct validation artifacts.
    """
    # 1. Setup — use AsyncMock for all async market data calls
    mock_md = AsyncMock(spec=MarketDataService)
    mock_md.get_ohlcv.return_value = make_ohlcv_buy_signal()
    mock_md.get_market_metrics.return_value = {
        "volatility": 0.05, "momentum": 0.03, "drawdown": 0.01
    }

    trust = TrustService()
    risk = RiskService()
    sm = CapitalStateMachine(trust, initial_mode=AgentMode.GROWTH)
    ts = TradingService(mock_md, risk, trust, sm)

    # Ensure mode is GROWTH
    sm.current_mode = AgentMode.GROWTH

    # Mock sandbox balance via AsyncMock
    trust.get_sandbox_balance = AsyncMock(return_value=1000.0)

    # 2. Trigger Trade Signal Logic
    await ts.get_trade_signal("BTC/USDT")

    # 3. Verify Artifacts in Trust History
    events = [h["event"] for h in trust.history]
    print(f"Events emitted: {events}")

    # Expected: strategy_checkpoint -> trade_intent
    assert "strategy_checkpoint" in events, f"strategy_checkpoint not in {events}"
    assert "trade_intent" in events, f"trade_intent not in {events}"

    # Check strategy_checkpoint structure
    checkpoint = next(h for h in trust.history if h["event"] == "strategy_checkpoint")
    assert checkpoint["artifact_hash"].startswith("0x")

    # 4. Trigger Mode Switch — High Drawdown -> Defensive Action
    heavy_metrics = {"volatility": 0.05, "momentum": 0.01, "drawdown": 0.10}
    await sm.transition(heavy_metrics)

    events = [h["event"] for h in trust.history]
    assert "defensive_action" in events, f"defensive_action not in {events}"

    # 5. High Volatility -> Risk Check (generic mode switch)
    vol_metrics = {"volatility": 0.12, "momentum": 0.01, "drawdown": 0.02}
    await sm.transition(vol_metrics)

    events = [h["event"] for h in trust.history]
    assert "risk_check" in events, f"risk_check not in {events}"


@pytest.mark.asyncio
async def test_risk_rejection_artifact():
    """
    Verifies that a trade rejected by risk produces a risk_rejection artifact.
    The drawdown (0.12) exceeds RISK_MAX_DRAWDOWN (0.08), so risk should reject.
    """
    mock_md = AsyncMock(spec=MarketDataService)
    mock_md.get_ohlcv.return_value = make_ohlcv_buy_signal()
    mock_md.get_market_metrics.return_value = {
        "volatility": 0.05, "momentum": 0.03, "drawdown": 0.12
    }

    trust = TrustService()
    risk = RiskService()
    ts = TradingService(mock_md, risk, trust)

    # Mock sandbox balance
    trust.get_sandbox_balance = AsyncMock(return_value=1000.0)

    await ts.get_trade_signal("BTC/USDT")

    events = [h["event"] for h in trust.history]
    print(f"Events emitted: {events}")

    assert "strategy_checkpoint" in events, f"strategy_checkpoint not in {events}"
    assert "risk_rejection" in events, f"risk_rejection not in {events}"
    assert "trade_intent" not in events, f"trade_intent should not be in {events}"
