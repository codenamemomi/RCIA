import asyncio
import logging
from api.v1.services.yield_optimization import YieldService
from api.v1.services.hedge import HedgeService
from core.config import settings

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def main():
    print("\n" + "="*40)
    print("--- RCIA Phase 3 Verification ---")
    print("="*40 + "\n")
    
    # 1. Yield Optimization Test
    print("--- Test 1: Yield Optimization (Allocating Idle Capital) ---")
    ys = YieldService()
    pools = ys.evaluate_pools()
    print(f"Found {len(pools)} pools.")
    
    allocation = ys.get_allocation_strategy(amount=50000)
    print(f"Allocation Strategy: {allocation}")

    # 2. Hedge Logic Test (High Volatility)
    print("\n--- Test 2: Hedging (High Volatility Protection) ---")
    hs = HedgeService()
    
    # Simulate high volatility market
    current_exposure = 100000
    high_volatility = 0.18 # > SM_VOLATILITY_MEDIUM (0.10)
    
    req = hs.calculate_hedge_requirement(current_exposure, high_volatility)
    print(f"Hedge Requirement: {req}")
    
    signals = hs.generate_hedge_signals("BTC/USDT", req)
    print(f"Hedge Signal: {signals}")

    # 3. Hedge Logic Test (Low Volatility)
    print("\n--- Test 3: Hedging (Low Volatility / No Requirement) ---")
    low_volatility = 0.05
    req_low = hs.calculate_hedge_requirement(current_exposure, low_volatility)
    signals_low = hs.generate_hedge_signals("BTC/USDT", req_low)
    print(f"Hedge Signal: {signals_low}")

    print("\n" + "="*40)

if __name__ == "__main__":
    asyncio.run(main())
