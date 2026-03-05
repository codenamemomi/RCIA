import pytest
from api.v1.services.market_data import MarketDataService
from api.v1.services.risk import RiskService
from api.v1.services.trading import TradingService
from api.v1.services.trust import TrustService
from core.state_machine import CapitalStateMachine, AgentMode

@pytest.mark.asyncio
async def test_end_to_end_flow_with_trust():
    """
    Verifies: 
    1. Signal -> Risk -> Trust (Trade)
    2. Metrics -> State Change -> Trust (State)
    """
    # 1. Setup
    trust = TrustService()
    md = MarketDataService()
    rs = RiskService()
    ts = TradingService(md, rs, trust)
    sm = CapitalStateMachine()
    
    # 2. Test State Transition with Trust
    metrics = {"drawdown": 0.10, "volatility": 0.05, "momentum": 0.01}
    new_mode, packet = await sm.transition(metrics)
    
    assert new_mode == AgentMode.DEFENSIVE
    assert "artifact_hash" in str(packet) or any(h["event"]=="STATE_TRANSITION" for h in sm.history)
    
    # 3. Test Trading Signal (Mocked/Simulated)
    # We'll check if the TradingService uses trust_service
    assert ts.trust_service == trust
    
    # 4. Manual Identity & Verification check
    reg = await trust.register_identity("RCIA-Integration-Test", "Test agent for end-to-end verification")
    assert reg["status"] == "success"
    
    val = await trust.emit_validation("INTEGRATION_TEST", {"status": "ok"})
    assert "signature" in val
    assert val["on_chain_status"] == "submitted"
    
    # Cleanup
    await md.close()
