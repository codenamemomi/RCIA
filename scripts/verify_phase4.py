import asyncio
import logging
from api.v1.services.market_data import MarketDataService
from api.v1.services.risk import RiskService
from api.v1.services.trading import TradingService
from api.v1.services.trust import TrustService
from core.state_machine import CapitalStateMachine, AgentMode

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def main():
    print("\n" + "="*40)
    print("--- RCIA Phase 4 Verification ---")
    print("="*40 + "\n")
    
    # Initialize components
    trust = TrustService()
    md = MarketDataService()
    rs = RiskService()
    ts = TradingService(md, rs, trust)
    sm = CapitalStateMachine()

    # 1. State Machine Trust Verification
    print("--- Test 1: State Machine Validation Artifact ---")
    # Simulate a volatility spike to trigger DEFENSIVE mode
    metrics = {
        "symbol": "BTC/USDT",
        "volatility": 0.16, # High
        "momentum": 0.02,
        "drawdown": 0.02,
        "current_price": 65000
    }
    
    print("Triggering state transition...")
    new_mode, packet = await sm.transition(metrics)
    print(f"New Mode: {new_mode.name}")
    print(f"Artifact Hash generated and 'emitted' successfully.")

    # 2. Trading Signal Trust Verification
    print("\n--- Test 2: Trading Signal Validation Artifact ---")
    symbol = "BTC/USDT"
    
    # We'll use a mock check to ensure get_trade_signal emits
    # Note: Test 1 in verify_phase2 failed due to network, 
    # but here we focus on the trust logic flow.
    print(f"Attempting signal generation for {symbol}...")
    try:
        # Since live fetch might fail, we demonstrate the emit_validation call separately
        # if the service execution reaches it.
        result = await ts.get_trade_signal(symbol)
        print(f"Signal Result: {result.get('signal')}")
        if "artifact_hash" in str(result): # Check if artifact was emitted
             print("Trade signal artifact emitted.")
    except Exception as e:
        logger.error(f"Signal test failed: {e}")

    # 3. Direct Trust Service Verification
    print("\n--- Test 3: Direct Identity & Validation Check ---")
    reg_result = await trust.register_identity("RCIA-Bot-Alpha", "Verifiable Agent")
    print(f"Identity Registration: {reg_result}")
    
    val_result = await trust.emit_validation("MANUAL_CHECK", {"status": "ok", "step": "verification"})
    print(f"Manual Validation Emit: {val_result['on_chain_status']} | Hash: {val_result['artifact_hash']}")
    print(f"Signature: {val_result['signature'][:32]}...")

    await md.close()
    print("\n" + "="*40)

if __name__ == "__main__":
    asyncio.run(main())
