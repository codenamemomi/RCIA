import asyncio
import logging
import json
import time
from typing import Dict, Any
from api.v1.services.market_data import MarketDataService
from api.v1.services.risk import RiskService
from api.v1.services.trading import TradingService
from api.v1.services.trust import TrustService
from api.v1.services.yield_optimization import YieldService
from api.v1.services.hedge import HedgeService
from core.state_machine import CapitalStateMachine, AgentMode
from core.config import settings

# Setup logging with a nice format for the demo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RCIA-Demo")

class MockMarketDataService(MarketDataService):
    """Mocks market data for smooth demo progression"""
    def __init__(self):
        super().__init__()
        self.mock_volatility = 0.04
        self.mock_momentum = 0.03
        self.mock_price = 65000.0

    async def get_market_metrics(self, symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "volatility": self.mock_volatility,
            "momentum": self.mock_momentum,
            "drawdown": 0.01,
            "current_price": self.mock_price
        }

    async def get_ohlcv(self, symbol: str, timeframe='1h', limit=30):
        # Return a simple upward trend for GROWTH mode initially
        base_price = self.mock_price
        return [[0, 0, 0, 0, base_price * (1 + i*0.001)] for i in range(limit)]

async def run_demo():
    print("\n" + "="*60)
    print("      🚀 RCIA VERIFIABLE CAPITAL INTELLIGENCE DEMO 🚀      ")
    print("="*60 + "\n")

    # 1. Initialization
    logger.info("Initializing RCIA Intelligence Engine...")
    trust = TrustService()
    md = MockMarketDataService()
    rs = RiskService()
    sm = CapitalStateMachine(trust_service=trust)
    yield_service = YieldService(trust)
    hedge_service = HedgeService(trust)
    ts = TradingService(md, rs, trust, state_machine=sm, yield_service=yield_service, hedge_service=hedge_service)

    # Register Identity (ERC-8004)
    logger.info("Step 1: Registering Agent Identity on ERC-8004 Layer...")
    await trust.register_identity(settings.AGENT_NAME, "Autonomous Sharpe-Optimized Trading Agent")
    await asyncio.sleep(1)

    # 2. Trigger Growth Trade
    print("\n" + "-"*20 + " SCENARIO: GROWTH MOMENTUM " + "-"*20)
    logger.info("Market Condition: High Momentum, Low Volatility Detected.")
    md.mock_volatility = 0.04
    md.mock_momentum = 0.03
    
    # Check for transitions
    metrics = await md.get_market_metrics("BTC/USDT")
    mode, packet = await sm.transition(metrics)
    logger.info(f"System Mode: {mode.name}")
    
    # Generate Signal & Execute
    logger.info("Analyzing signals for BTC/USDT...")
    signal_result = await ts.get_trade_signal("BTC/USDT")
    
    if signal_result.get("signal") == "BUY":
        logger.info(f"✅ Growth Trade Triggered: {signal_result['signal']} {signal_result['amount']} BTC/USDT")
        logger.info(f"📜 Validation Artifact Emitted. Tx: {signal_result['execution']['tx_hash']}")
    
    await asyncio.sleep(2)

    # 3. Simulate Volatility Spike
    print("\n" + "-"*20 + " SCENARIO: VOLATILITY SPIKE " + "-"*20)
    logger.info("⚠️ WARNING: Black Swan Event Detected! Volatility surging...")
    md.mock_volatility = 0.15 # Above HIGH threshold (0.12)
    md.mock_momentum = -0.05
    
    # Trigger Mode Switch
    metrics = await md.get_market_metrics("BTC/USDT")
    logger.info("Updating State Machine Intelligence...")
    new_mode, transition_packet = await sm.transition(metrics)
    
    if new_mode == AgentMode.DEFENSIVE:
        logger.info(f"🛡️ Automatic Defensive Switch: {AgentMode.GROWTH.name} -> {AgentMode.DEFENSIVE.name}")
        logger.info(f"Reason: {transition_packet['trigger_reason']}")
        logger.info(f"📜 Transition Artifact Hash: {sm.trust_service.history[-1]['artifact_hash']}")
    
    await asyncio.sleep(2)

    # 4. Show De-risking Signal
    logger.info("Requesting post-crash trading instructions...")
    defensive_signal = await ts.get_trade_signal("BTC/USDT")
    logger.info(f"🚨 Defensive Action: {defensive_signal['signal']} | Reason: {defensive_signal['reason']}")

    await asyncio.sleep(2)

    # 5. Reputation Score Update
    print("\n" + "-"*20 + " FEEDBACK LOOP: REPUTATION " + "-"*20)
    logger.info("Reporting Trade Outcome to Reputation Registry...")
    # Simulate a successful de-risking outcome
    outcome = await trust.report_outcome("BTC_DEFENSIVE_EXIT", 0.015, True)
    logger.info(f"Outcome Logged. Tx: {outcome['tx_hash']}")
    
    logger.info("Querying On-Chain Reputation Score...")
    score = await trust.get_reputation()
    # For demo purposes, we'll manually increment if it's mock
    if settings.SIMULATE_ON_CHAIN:
        score = 85 # Simulated score after successful actions
    
    logger.info(f"⭐ Current Agent Reputation Score: {score}/100")

    print("\n" + "="*60)
    print("            DEMO COMPLETED SUCCESSFULLY ✅            ")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_demo())
