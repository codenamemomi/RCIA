import logging
import numpy as np
import ccxt.async_support as ccxt
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from core.config import settings

logger = logging.getLogger(__name__)

COINGECKO_MAP = {
    "BTC/USDT": "bitcoin",
    "ETH/USDT": "ethereum"
}

CRYPTOCOMPARE_MAP = {
    "BTC/USDT": "BTC",
    "ETH/USDT": "ETH"
}

class MarketDataService:
    def __init__(self, exchange_id: str = None):
        self.exchange_id = exchange_id or settings.DEFAULT_EXCHANGE
        self.exchange = getattr(ccxt, self.exchange_id)()
        logger.info(f"MarketDataService initialized with {self.exchange_id}")

    async def get_market_metrics(self, symbol: str = "BTC/USDT") -> Dict[str, Any]:
        """
        Fetches data using CryptoCompare (aggregator) and calculates key metrics.
        Falls back to mock data if MOCK_MARKET_DATA is True or if fetching fails.
        """
        if settings.MOCK_MARKET_DATA:
            logger.info(f"Using mock market data for {symbol}")
            return self._get_mock_metrics(symbol)

        try:
            # Try CryptoCompare (Aggregator) first
            if symbol in CRYPTOCOMPARE_MAP:
                try:
                    return await self._get_cryptocompare_metrics(symbol)
                except Exception as cc_err:
                    logger.warning(f"CryptoCompare fetch failed for {symbol}: {cc_err}. Trying CCXT...")

            # Fallback to CCXT
            ohlcv = await self._fetch_with_retries(symbol, timeframe='1h', limit=24)
            
            if not ohlcv or len(ohlcv) < 2:
                raise ValueError(f"Insufficient data for {symbol}")

            closes = [kline[4] for kline in ohlcv]
            return self._calculate_metrics_from_closes(symbol, closes, source="ccxt")

        except Exception as e:
            logger.error(f"Error fetching market metrics for {symbol}: {e}. Falling back to mock.")
            return self._get_mock_metrics(symbol)

    async def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> List[List[float]]:
        """
        Fetches OHLCV data with aggregator/mock fallback.
        """
        if settings.MOCK_MARKET_DATA:
            return self._get_mock_ohlcv(limit)

        try:
            # Try CryptoCompare
            if symbol in CRYPTOCOMPARE_MAP:
                try:
                    return await self._get_cryptocompare_ohlcv(symbol, limit)
                except Exception as cc_err:
                    logger.warning(f"CryptoCompare OHLCV failed for {symbol}: {cc_err}. Trying CCXT...")

            return await self._fetch_with_retries(symbol, timeframe, limit)
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}. Falling back to mock.")
            return self._get_mock_ohlcv(limit)

    async def _get_cryptocompare_metrics(self, symbol: str) -> Dict[str, Any]:
        """Fetches metrics from CryptoCompare API"""
        fsym = CRYPTOCOMPARE_MAP[symbol]
        url = f"{settings.CRYPTOCOMPARE_API_URL}/v2/histohour?fsym={fsym}&tsym=USD&limit=24"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            if data.get("Response") == "Error":
                raise Exception(f"CryptoCompare Error: {data.get('Message')}")

            closes = [entry["close"] for entry in data["Data"]["Data"]]
            return self._calculate_metrics_from_closes(symbol, closes, source="cryptocompare")

    async def _get_cryptocompare_ohlcv(self, symbol: str, limit: int) -> List[List[float]]:
        """Fetches price history from CryptoCompare and formats as OHLCV"""
        fsym = CRYPTOCOMPARE_MAP[symbol]
        url = f"{settings.CRYPTOCOMPARE_API_URL}/v2/histohour?fsym={fsym}&tsym=USD&limit={limit}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            if data.get("Response") == "Error":
                raise Exception(f"CryptoCompare Error: {data.get('Message')}")
            
            # Format: [timestamp, open, high, low, close, volume]
            ohlcv = []
            for entry in data["Data"]["Data"]:
                ohlcv.append([
                    entry["time"] * 1000, 
                    entry["open"], 
                    entry["high"], 
                    entry["low"], 
                    entry["close"], 
                    entry["volumefrom"]
                ])
            return ohlcv

    def _calculate_metrics_from_closes(self, symbol: str, closes: List[float], source: str = "aggregator") -> Dict[str, Any]:
        """Internal helper to calculate statistics from a series of close prices"""
        current_price = closes[-1]
        previous_price = closes[0]
        
        momentum = (current_price - previous_price) / previous_price if previous_price != 0 else 0
        returns = np.diff(np.log(closes))
        volatility = float(np.std(returns)) if len(returns) > 0 else 0
        
        high_price = max(closes)
        drawdown = (high_price - current_price) / high_price if high_price != 0 else 0
        
        return {
            "symbol": symbol,
            "exchange": source,
            "current_price": current_price,
            "momentum": momentum,
            "volatility": volatility,
            "drawdown": drawdown,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }

    def _get_mock_ohlcv(self, limit: int) -> List[List[float]]:
        import random
        import time
        base_price = 65000
        ohlcv = []
        for i in range(limit):
            timestamp = int(time.time() * 1000) - (limit - i) * 3600000
            open_p = base_price + random.uniform(-100, 100)
            high_p = open_p + random.uniform(0, 50)
            low_p = open_p - random.uniform(0, 50)
            close_p = (high_p + low_p) / 2
            vol = random.uniform(10, 100)
            ohlcv.append([timestamp, open_p, high_p, low_p, close_p, vol])
            base_price = close_p
        return ohlcv

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
