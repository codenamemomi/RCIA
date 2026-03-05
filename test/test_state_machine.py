import pytest
from core.state_machine import CapitalStateMachine, AgentMode
from core.config import settings

@pytest.mark.asyncio
async def test_state_machine_initialization():
    sm = CapitalStateMachine()
    # Default changed to GROWTH in Phase 4 for certain configurations
    assert sm.current_mode == AgentMode.GROWTH
    assert sm.get_status()["current_mode"] == "GROWTH"

@pytest.mark.asyncio
async def test_transition_to_defensive_on_drawdown():
    sm = CapitalStateMachine(initial_mode=AgentMode.YIELD)
    metrics = {
        "volatility": 0.05,
        "momentum": 0.01,
        "drawdown": 0.10  # > 0.05
    }
    new_mode, validation = await sm.transition(metrics)
    assert sm.current_mode == AgentMode.DEFENSIVE
    assert new_mode == AgentMode.DEFENSIVE
    assert validation["to_state"] == "DEFENSIVE"
    assert "Drawdown" in validation["trigger_reason"]

@pytest.mark.asyncio
async def test_transition_to_hedge_on_volatility():
    sm = CapitalStateMachine(initial_mode=AgentMode.YIELD)
    metrics = {
        "volatility": 0.12, # > 0.10 (SM_VOLATILITY_MEDIUM)
        "momentum": 0.01,
        "drawdown": 0.02
    }
    new_mode, validation = await sm.transition(metrics)
    assert sm.current_mode == AgentMode.HEDGE
    assert new_mode == AgentMode.HEDGE
    assert validation["to_state"] == "HEDGE"
    assert "Medium volatility" in validation["trigger_reason"]

@pytest.mark.asyncio
async def test_transition_to_growth():
    sm = CapitalStateMachine(initial_mode=AgentMode.YIELD)
    metrics = {
        "volatility": 0.05, # < 0.08 (SM_VOLATILITY_LOW)
        "momentum": 0.05,   # > 0.02 (SM_MOMENTUM_GROWTH)
        "drawdown": 0.01
    }
    new_mode, validation = await sm.transition(metrics)
    assert sm.current_mode == AgentMode.GROWTH
    assert new_mode == AgentMode.GROWTH
    assert validation["to_state"] == "GROWTH"
    assert "High momentum" in validation["trigger_reason"]

@pytest.mark.asyncio
async def test_validation_packet_structure():
    sm = CapitalStateMachine()
    metrics = {"volatility": 0.20, "momentum": 0, "drawdown": 0}
    new_mode, validation = await sm.transition(metrics)
    
    # Check that we actually got a validation packet (transition occurred)
    assert validation != {}
    assert "version" in validation
    assert "event" in validation
    assert "agent_id" in validation
    assert "from_state" in validation
    assert "to_state" in validation
    assert "trigger_metrics" in validation
    assert "trigger_reason" in validation
    assert "timestamp" in validation
    assert validation["event"] == "STATE_TRANSITION"
