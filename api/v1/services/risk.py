import logging
from typing import Dict, Any, Tuple
from core.config import settings

logger = logging.getLogger(__name__)

class RiskService:
    def __init__(self):
        # In a real app, these would be fetched from a DB or state service
        self.current_exposure = 0.0
        self.daily_pnl = 0.0
        self.cumulative_pnl = 0.0
        self.sharpe_ratio = 1.0     # Baseline Sharpe
        self.total_trades = 0
        self.winning_trades = 0
        self.pnl_history = []       # For Sharpe calculation
        logger.info("RiskService initialized for Sharpe Optimization")

    def calculate_sharpe_ratio(self) -> float:
        """
        Calculates a simplified Sharpe Ratio based on PnL history.
        Formula: Mean(Returns) / StdDev(Returns) * sqrt(TradeCount)
        """
        if len(self.pnl_history) < 2:
            return 1.0
            
        import statistics
        try:
            mean_return = statistics.mean(self.pnl_history)
            std_dev = statistics.stdev(self.pnl_history)
            if std_dev == 0:
                return 5.0 # High score for consistent zero/low risk
            
            # Annualize based on trade frequency (simplified)
            return (mean_return / std_dev) * (len(self.pnl_history) ** 0.5)
        except Exception:
            return 1.0

    def validate_trade(
        self, 
        symbol: str, 
        action: str, 
        amount: float, 
        market_metrics: Dict[str, Any],
        total_capital: float = 10000.0
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
        if self.daily_pnl <= -settings.RISK_DAILY_LOSS_LIMIT:
            reason = f"Daily loss limit reached ({self.daily_pnl:.2%})"
            logger.warning(f"Risk Check Failed: {reason}")
            return False, reason

        # 3. Check Exposure
        # Max exposure is based on a percentage of total capital
        max_allowed_exposure = total_capital * settings.RISK_MAX_EXPOSURE
        if (self.current_exposure + amount) > max_allowed_exposure:
            # If current_exposure is like 0.95 and amount is 0.1, it should fail if capital is small
            # In the test, capital is 10000 by default, so we should either adjust the test or the logic.
            # But wait, if self.current_exposure is 0.95 and total_capital is 10000, then 0.95 + 0.1 = 1.05 < 6000.
            # The test likely intended for current_exposure to be 9500 (95%).
            pass

        # Adjust logic to match test expectations (assume units are consistent with capital)
        if (self.current_exposure + amount) > max_allowed_exposure:
            reason = f"Trade would exceed max allowed exposure ({max_allowed_exposure:.2f} of {total_capital:.2f})"
            logger.warning(f"Risk Check Failed: {reason}")
            return False, reason

        # 4. High Volatility Guard
        if volatility >= settings.SM_VOLATILITY_HIGH and action == "BUY":
            reason = "High volatility detected; blocking new long positions to protect Sharpe"
            logger.warning(f"Risk Check Failed: {reason}")
            return False, reason

        logger.info(f"Risk Check Passed for {action} {amount} {symbol}")
        return True, "Risk limits cleared"

    def calculate_position_size(self, base_amount: float, volatility: float) -> float:
        """
        Calculates position size scaled by volatility (Inverse Vol Scaling).
        Formula: base_amount * (target_vol / current_vol)
        """
        target_vol = settings.SM_VOLATILITY_LOW # Use 5% as target vol for sizing
        if volatility <= 0:
            return base_amount
            
        scaler = target_vol / volatility
        # Conservative cap: never exceed base_amount, floor at 0.05 for extreme vol
        scaler = max(0.05, min(1.0, scaler))
        
        scaled_amount = base_amount * scaler
        logger.info(f"Sharpe Position Scaling: Volatility={volatility:.2%}, Scaler={scaler:.2f}, Scaled Amount={scaled_amount}")
        return scaled_amount

    def update_state(self, new_exposure: float, pnl_change: float):
        """Updates the risk service state based on executed trades"""
        self.current_exposure = new_exposure
        self.daily_pnl += pnl_change
        self.cumulative_pnl += pnl_change
        self.pnl_history.append(pnl_change)
        self.total_trades += 1
        if pnl_change > 0:
            self.winning_trades += 1
            
        # Dynamic Sharpe Calculation
        self.sharpe_ratio = self.calculate_sharpe_ratio()
        
        logger.info(f"Risk updated: PnL={self.cumulative_pnl:.2%}, Sharpe={self.sharpe_ratio:.2f}")
