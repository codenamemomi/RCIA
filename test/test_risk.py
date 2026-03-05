import pytest
from api.v1.services.risk import RiskService
from core.config import settings

def test_risk_check_passed():
    risk = RiskService()
    metrics = {"drawdown": 0.02, "volatility": 0.05}
    # Should pass
    allowed, reason = risk.validate_trade("BTC/USDT", "BUY", 0.1, metrics)
    assert allowed is True
    assert "cleared" in reason

def test_risk_check_drawdown_failed():
    risk = RiskService()
    # Drawdown 12% > threshold 10%
    metrics = {"drawdown": 0.12, "volatility": 0.05}
    allowed, reason = risk.validate_trade("BTC/USDT", "BUY", 0.1, metrics)
    assert allowed is False
    assert "exceeds limit" in reason

def test_risk_check_exposure_failed():
    risk = RiskService()
    # Over exposure
    risk.update_state(0.95, 0) # Current 95%
    metrics = {"drawdown": 0.01, "volatility": 0.05}
    # 0.95 + 0.10 = 1.05 > settings.RISK_MAX_EXPOSURE (1.0 or 0.8 depending on config)
    allowed, reason = risk.validate_trade("BTC/USDT", "BUY", 0.1, metrics)
    assert allowed is False
    assert "exposure" in reason

def test_risk_check_high_volatility_buy_blocked():
    risk = RiskService()
    # Volatility 20% > high threshold
    metrics = {"drawdown": 0.01, "volatility": 0.20}
    allowed, reason = risk.validate_trade("BTC/USDT", "BUY", 0.1, metrics)
    assert allowed is False
    assert "High volatility" in reason

def test_risk_check_high_volatility_sell_allowed():
    risk = RiskService()
    # Volatility high, but SELL (hedge/exit) should be allowed
    metrics = {"drawdown": 0.01, "volatility": 0.20}
    allowed, reason = risk.validate_trade("BTC/USDT", "SELL", 0.1, metrics)
    assert allowed is True
