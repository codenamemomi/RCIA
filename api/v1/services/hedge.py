import logging
from typing import Dict, Any
from core.config import settings

logger = logging.getLogger(__name__)

from api.v1.services.trust import TrustService

class HedgeService:
    def __init__(self, trust_service: TrustService = None):
        self.trust_service = trust_service or TrustService()
        logger.info("HedgeService initialized with Trust layer")

    async def calculate_hedge_requirement(self, current_exposure: float, volatility: float) -> Dict[str, Any]:
        """
        Calculates the required hedge position based on exposure and volatility.
        """
        # Linear hedge scaling: more volatility -> more hedge
        # Base hedge ratio from settings, scaled by volatility factor
        vol_factor = min(volatility / settings.SM_VOLATILITY_HIGH, 2.0)
        required_hedge_ratio = settings.HEDGE_RATIO * vol_factor
        
        hedge_amount = current_exposure * required_hedge_ratio
        
        logger.info(f"Hedge calc: Exposure={current_exposure}, Vol={volatility:.2%}, Required Hedge={hedge_amount:.2f}")
        
        result = {
            "is_required": volatility > settings.SM_VOLATILITY_MEDIUM,
            "exposure": current_exposure,
            "hedge_amount": hedge_amount,
            "hedge_ratio": required_hedge_ratio
        }
        
        if result["is_required"]:
            # Emit validation artifact for ERC-8004
            await self.trust_service.emit_validation("HEDGE_ACTIVATION", result)
            
        return result

    def generate_hedge_signals(self, symbol: str, req: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates the trade signals needed to enter/exit a hedge.
        """
        if req["is_required"]:
            return {
                "symbol": symbol,
                "action": "SELL_SHORT", # Hedging involves shorting
                "amount": req["hedge_amount"],
                "reason": "Volatility protection active"
            }
        
        return {"action": "NONE", "reason": "Volatility below hedge threshold"}
