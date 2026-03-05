import logging
import numpy as np
import ccxt.async_support as ccxt
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from core.config import settings

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self, exchange_id: str = None):
        self.exchange_id = exchange_id or settings.DEFAULT_EXCHANGE
        self.exchange = getattr(ccxt, self.exchange_id)()
        logger.info(f"MarketDataService initialized with {self.exchange_id}")

    async def get_market_metrics(self, symbol: str = "BTC/USDT") -> Dict[str, Any]:
        """
        Fetches OHLCV data using CCXT and calculates key metrics.
        Falls back to mock data if MOCK_MARKET_DATA is True or if fetching fails.
        """
        if settings.MOCK_MARKET_DATA:
            logger.info(f"Using mock market data for {symbol}")
            return self._get_mock_metrics(symbol)

        try:
            # Fetch last 24h worth of hourly candles (24 candles)
            ohlcv = await self._fetch_with_retries(symbol, timeframe='1h', limit=24)
            
            if not ohlcv or len(ohlcv) < 2:
                raise ValueError(f"Insufficient data for {symbol}")

            closes = [kline[4] for kline in ohlcv]
            
            # Calculate Metrics
            current_price = closes[-1]
            previous_price = closes[0]
            
            # Momentum: Simple percentage change over the period
            momentum = (current_price - previous_price) / previous_price if previous_price != 0 else 0
            
            # Volatility: Standard deviation of log returns
            returns = np.diff(np.log(closes))
            volatility = float(np.std(returns)) if len(returns) > 0 else 0

            # Drawdown (Current vs high in period)
            high_price = max(closes)
            drawdown = (high_price - current_price) / high_price if high_price != 0 else 0

            metrics = {
                "symbol": symbol,
                "exchange": self.exchange_id,
                "current_price": current_price,
                "momentum": momentum,
                "volatility": volatility,
                "drawdown": drawdown,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
            }
            logger.debug(f"Calculated metrics for {symbol}: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching market metrics for {symbol}: {e}. Falling back to mock.")
            return self._get_mock_metrics(symbol)

    def _get_mock_metrics(self, symbol: str) -> Dict[str, Any]:
        import random
        return {
            "symbol": symbol,
            "exchange": "mock",
            "current_price": random.uniform(60000, 70000),
            "momentum": random.uniform(-0.05, 0.05),
            "volatility": random.uniform(0.01, 0.20),
            "drawdown": random.uniform(0, 0.15),
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }

    async def _fetch_with_retries(self, symbol: str, timeframe: str, limit: int) -> List[List[float]]:
        last_error = None
        for attempt in range(settings.CCXT_RETRY_ATTEMPTS):
            try:
                return await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                last_error = e
                logger.warning(f"CCXT fetch attempt {attempt + 1} failed for {symbol}: {e}")
                if attempt < settings.CCXT_RETRY_ATTEMPTS - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"Unexpected error in CCXT fetch: {e}")
                raise
        
        raise last_error or Exception(f"Failed to fetch data for {symbol} after {settings.CCXT_RETRY_ATTEMPTS} attempts")

    async def close(self):
        """Close the CCXT exchange connection"""
        await self.exchange.close()
