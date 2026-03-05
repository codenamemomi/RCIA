import logging
from typing import Dict, Any, List, Optional
from api.v1.services.market_data import MarketDataService
from api.v1.services.risk import RiskService
from api.v1.services.trust import TrustService
from core.config import settings

logger = logging.getLogger(__name__)

from core.state_machine import CapitalStateMachine, AgentMode
from api.v1.services.yield_optimization import YieldService
from api.v1.services.hedge import HedgeService

class TradingService:
    def __init__(
        self, 
        market_data: MarketDataService, 
        risk_service: RiskService, 
        trust_service: TrustService,
        state_machine: CapitalStateMachine = None,
        yield_service: YieldService = None,
        hedge_service: HedgeService = None
    ):
        self.market_data = market_data
        self.risk_service = risk_service
        self.trust_service = trust_service
        self.state_machine = state_machine or CapitalStateMachine()
        self.yield_service = yield_service or YieldService(trust_service)
        self.hedge_service = hedge_service or HedgeService(trust_service)
        logger.info("TradingService initialized with Mode-Aware architecture")

    async def get_trade_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Mode-Aware signal generation:
        - GROWTH: Momentum Strategy
        - YIELD: Stablecoin Allocation
        - HEDGE: Protective Positions
        - DEFENSIVE: Exit/De-risk
        """
        current_mode = self.state_machine.current_mode
        metrics = await self.market_data.get_market_metrics(symbol)
        
        if current_mode == AgentMode.GROWTH:
            return await self._get_momentum_signal(symbol, metrics)
            
        elif current_mode == AgentMode.YIELD:
            # Mock amount: $10k for yield allocation
            allocation = await self.yield_service.get_allocation_strategy(10000.0)
            
            # Phase 5: Execute yield allocation on-chain
            execution_result = await self.yield_service.execute_yield_allocation(allocation)
            
            return {
                "symbol": "STABLES",
                "mode": current_mode,
                "strategy": allocation,
                "execution": execution_result,
                "metrics": metrics
            }
            
        elif current_mode == AgentMode.HEDGE:
            hedge_req = await self.hedge_service.calculate_hedge_requirement(
                self.risk_service.current_exposure, 
                metrics["volatility"]
            )
            hedge_signal = self.hedge_service.generate_hedge_signals(symbol, hedge_req)
            return {
                "symbol": symbol,
                "mode": current_mode,
                "hedge_req": hedge_req,
                "signal": hedge_signal,
                "metrics": metrics
            }
            
        elif current_mode == AgentMode.DEFENSIVE:
            return {
                "symbol": symbol,
                "mode": current_mode,
                "signal": "EXIT_ALL",
                "reason": "Risk limits exceeded or crash detected",
                "metrics": metrics
            }

        return {"symbol": symbol, "signal": "HOLD", "mode": current_mode, "metrics": metrics}

    async def _get_momentum_signal(self, symbol: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Momentum Strategy logic (Internal)"""
        try:
            ohlcv = await self.market_data.get_ohlcv(symbol, timeframe='1h', limit=settings.MA_SLOW_PERIOD + 1)
            closes = [k[4] for k in ohlcv]
            
            fast_ma = sum(closes[-settings.MA_FAST_PERIOD:]) / settings.MA_FAST_PERIOD
            slow_ma = sum(closes[-settings.MA_SLOW_PERIOD:]) / settings.MA_SLOW_PERIOD
            
            signal = "HOLD"
            if fast_ma > slow_ma * 1.005:
                signal = "BUY"
            elif fast_ma < slow_ma * 0.995:
                signal = "SELL"

            if signal != "HOLD":
                # Phase 5: Volatility-based position scaling
                base_amount = settings.RISK_MAX_EXPOSURE * 0.1
                amount_to_trade = self.risk_service.calculate_position_size(base_amount, metrics["volatility"])
                
                is_safe, reason = self.risk_service.validate_trade(symbol, signal, amount_to_trade, metrics)
                
                if not is_safe:
                    return {"symbol": symbol, "signal": "HOLD", "rejected_reason": reason, "metrics": metrics}
                
                # Phase 2: Create, Sign, and Submit TradeIntent to Vault
                import time
                timestamp = int(time.time())
                
                # 1. Sign Intent
                signed_intent = self.trust_service.signer.sign_trade_intent(
                    agent_id=self.trust_service.agent_id,
                    action=signal,
                    amount=int(amount_to_trade * 10**18), # Assuming 18 decimals for vault
                    timestamp=timestamp
                )
                
                # 2. Submit to on-chain Risk Router / Vault
                execution_result = await self.trust_service.submit_trade_intent(signed_intent)
                
                # 3. Report outcome (Simulated success for demo)
                await self.trust_service.report_outcome(
                    event_id=f"TRADE_{symbol}_{timestamp}",
                    roi=0.02, # Example 2% ROI
                    success=True
                )

                return {
                    "symbol": symbol, 
                    "signal": signal, 
                    "amount": amount_to_trade, 
                    "execution": execution_result,
                    "metrics": metrics
                }

            return {"symbol": symbol, "signal": "HOLD", "metrics": metrics}

        except Exception as e:
            logger.error(f"Error in momentum strategy: {e}")
            return {"symbol": symbol, "signal": "ERROR", "error": str(e)}

        except Exception as e:
            logger.error(f"Error generating trade signal for {symbol}: {e}")
            return {"symbol": symbol, "signal": "ERROR", "error": str(e)}
