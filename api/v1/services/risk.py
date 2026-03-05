import logging
from typing import Dict, Any, Tuple
from core.config import settings

logger = logging.getLogger(__name__)

class RiskService:
    def __init__(self):
        # In a real app, these would be fetched from a DB or state service
        self.current_exposure = 0.0
        self.daily_pnl = 0.0
        logger.info("RiskService initialized")

    def validate_trade(
        self, 
        symbol: str, 
        action: str, 
        amount: float, 
        market_metrics: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Validates a trade intent against risk limits:
        1. Drawdown Limit
        2. Daily Loss Limit
        3. Maximum Portfolio Exposure
        """
        drawdown = market_metrics.get("drawdown", 0)
        volatility = market_metrics.get("volatility", 0)

        # 1. Check Drawdown
        if drawdown > settings.RISK_MAX_DRAWDOWN:
            reason = f"Total drawdown ({drawdown:.2%}) exceeds limit ({settings.RISK_MAX_DRAWDOWN:.2%})"
            logger.warning(f"Risk Check Failed: {reason}")
            return False, reason

        # 2. Check Daily Loss (Placeholder logic)
        if self.daily_pnl < -settings.RISK_DAILY_LOSS_LIMIT:
            reason = f"Daily loss limit reached ({self.daily_pnl:.2%})"
            logger.warning(f"Risk Check Failed: {reason}")
            return False, reason

        # 3. Check Exposure
        # Simplified: check if adding this amount exceeds max exposure
        if (self.current_exposure + amount) > settings.RISK_MAX_EXPOSURE:
            reason = f"Trade would exceed max exposure ({settings.RISK_MAX_EXPOSURE:.2%})"
            logger.warning(f"Risk Check Failed: {reason}")
            return False, reason

        # 4. High Volatility Guard
        if volatility > settings.SM_VOLATILITY_HIGH and action == "BUY":
            reason = "High volatility detected; blocking new long positions"
            logger.warning(f"Risk Check Failed: {reason}")
            return False, reason

        logger.info(f"Risk Check Passed for {action} {amount} {symbol}")
        return True, "Risk limits cleared"

    def update_state(self, new_exposure: float, pnl_change: float):
        """Updates the risk service state based on executed trades"""
        self.current_exposure = new_exposure
        self.daily_pnl += pnl_change
        logger.debug(f"Risk state updated: Exposure={self.current_exposure}, Daily PnL={self.daily_pnl}")
