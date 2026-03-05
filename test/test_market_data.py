import pytest
from unittest.mock import AsyncMock, patch
from api.v1.services.market_data import MarketDataService

@pytest.mark.asyncio
async def test_get_market_metrics_calculation():
    # Mock CCXT exchange
    mock_ohlcv = [
        [0, 100, 105, 95, 100, 1000],  # Start price 100
        [1, 100, 110, 100, 110, 1000], # Current price 110
    ]
    
    with patch("ccxt.async_support.binance") as mock_binance, \
         patch("api.v1.services.market_data.MarketDataService._get_cryptocompare_metrics", side_effect=Exception("Aggregator Fallback")), \
         patch("api.v1.services.market_data.settings.MOCK_MARKET_DATA", False):
        mock_instance = mock_binance.return_value
        mock_instance.fetch_ohlcv = AsyncMock(return_value=mock_ohlcv)
        mock_instance.close = AsyncMock()
        
        service = MarketDataService(exchange_id="binance")
        metrics = await service.get_market_metrics("BTC/USDT")
        
        # Momentum: (110 - 100) / 100 = 0.1
        assert metrics["momentum"] == 0.1
        
        # Current price
        assert metrics["current_price"] == 110
        
        # High price was 110, current is 110, so drawdown is 0
        assert metrics["drawdown"] == 0
        
        await service.close()

@pytest.mark.asyncio
async def test_drawdown_calculation():
    # Price dropped from 120 (high) to 108
    mock_ohlcv = [
        [0, 100, 120, 100, 120, 1000], # High 120
        [1, 120, 120, 100, 108, 1000], # Current 108
    ]
    
    with patch("ccxt.async_support.binance") as mock_binance, \
         patch("api.v1.services.market_data.MarketDataService._get_cryptocompare_metrics", side_effect=Exception("Aggregator Fallback")), \
         patch("api.v1.services.market_data.settings.MOCK_MARKET_DATA", False):
        mock_instance = mock_binance.return_value
        mock_instance.fetch_ohlcv = AsyncMock(return_value=mock_ohlcv)
        mock_instance.close = AsyncMock()
        
        service = MarketDataService(exchange_id="binance")
        metrics = await service.get_market_metrics("BTC/USDT")
        
        # Drawdown: (120 - 108) / 120 = 12 / 120 = 0.1
        assert metrics["drawdown"] == pytest.approx(0.1)
        
        await service.close()
