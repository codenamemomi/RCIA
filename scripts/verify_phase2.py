import asyncio
import logging
from api.v1.services.market_data import MarketDataService
from api.v1.services.risk import RiskService
from api.v1.services.trading import TradingService
from core.config import settings

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def main():
    print("\n" + "="*40)
    print("--- RCIA Phase 2 Verification ---")
    print("="*40 + "\n")
    
    # Initialize components
    md = MarketDataService()
    rs = RiskService()
    ts = TradingService(md, rs)
    
    symbol = "BTC/USDT"
    print(f"Generating trade signal for {symbol}...")
    
    # 1. Normal Check
    print("\n--- Test 1: Normal Signal Generation ---")
    try:
        result = await ts.get_trade_signal(symbol)
        print(f"Result: {result}")
    except Exception as e:
        logger.error(f"Test 1 failed: {e}")

    # 2. Risk Rejection Test (Injecting high drawdown)
    print("\n--- Test 2: Risk Rejection (Drawdown Breach) ---")
    try:
        # Mocking high drawdown in metrics
        fake_metrics = {
            "symbol": symbol,
            "current_price": 60000,
            "momentum": 0.05,
            "volatility": 0.05,
            "drawdown": 0.15, # > settings.RISK_MAX_DRAWDOWN (0.10)
            "timestamp": "2026-03-03T16:00:00Z"
        }
        
        is_safe, reason = rs.validate_trade(symbol, "BUY", 0.1, fake_metrics)
        print(f"Risk Check: is_safe={is_safe}, reason='{reason}'")
        
    except Exception as e:
        logger.error(f"Test 2 failed: {e}")

    # 3. Risk Rejection Test (Exposure Breach)
    print("\n--- Test 3: Risk Rejection (Exposure Breach) ---")
    try:
        rs.update_state(new_exposure=0.75, pnl_change=0)
        print(f"Current Exposure updated to: {rs.current_exposure}")
        
        # Try a trade that adds 0.1 occupancy
        is_safe, reason = rs.validate_trade(symbol, "BUY", 0.1, {"drawdown": 0.02, "volatility": 0.02})
        print(f"Risk Check (0.75 + 0.10): is_safe={is_safe}, reason='{reason}'")
        
    except Exception as e:
        logger.error(f"Test 3 failed: {e}")

    finally:
        await md.close()
        print("\n" + "="*40)

if __name__ == "__main__":
    asyncio.run(main())
