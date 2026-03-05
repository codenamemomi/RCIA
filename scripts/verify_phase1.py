import asyncio
import logging
from core.state_machine import CapitalStateMachine, AgentMode
from api.v1.services.market_data import MarketDataService

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def main():
    print("\n" + "="*40)
    print("--- RCIA Phase 1 Verification ---")
    print("="*40 + "\n")
    
    # Initialize components
    sm = CapitalStateMachine()
    md = MarketDataService()  # Uses default binance
    
    print(f"Initial State: {sm.get_status()['current_mode']}")
    
    # Fetch real market data
    symbol = "BTC/USDT"
    print(f"Fetching market metrics for {symbol}...")
    try:
        metrics = await md.get_market_metrics(symbol)
        print(f"Metrics: {metrics}")
        
        # Trigger transition
        print("\nFeeding metrics to state machine...")
        validation = sm.transition(metrics)
        
        if validation:
            print(f"\n[TRANSITION OCCURRED]")
            print(f"Path: {validation['from_state']} -> {validation['to_state']}")
            print(f"Reason: {validation.get('trigger_reason')}")
            print(f"Validation Packet: {validation}")
        else:
            print(f"\n[NO TRANSITION]")
            print(f"Current State: {sm.get_status()['current_mode']}")
            
    except Exception as e:
        logger.error(f"Verification failed: {e}")
    finally:
        await md.close()
        print("\n" + "="*40)

if __name__ == "__main__":
    asyncio.run(main())
