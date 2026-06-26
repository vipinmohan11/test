"""Unified OHLCV market data fetching across exchanges via ccxt."""
from __future__ import annotations

import pandas as pd
import ccxt

SUPPORTED_EXCHANGES = {
    "binance": ccxt.binance,
    "coinbase": ccxt.coinbase,
    "kraken": ccxt.kraken,
}


def get_exchange(exchange_id: str) -> ccxt.Exchange:
    if exchange_id not in SUPPORTED_EXCHANGES:
        raise ValueError(f"Unsupported exchange '{exchange_id}'. Choose from {list(SUPPORTED_EXCHANGES)}")
    return SUPPORTED_EXCHANGES[exchange_id]({"enableRateLimit": True})


def fetch_ohlcv(exchange_id: str, symbol: str, timeframe: str = "5m", limit: int = 300) -> pd.DataFrame:
    """Fetch OHLCV candles and return as a DataFrame indexed by UTC timestamp.

    symbol must be in ccxt unified form, e.g. 'BTC/EUR'.
    """
    exchange = get_exchange(exchange_id)
    raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    return df


def list_symbols(exchange_id: str, quote: str = "EUR") -> list[str]:
    """List tradeable symbols on the exchange quoted in the given currency."""
    exchange = get_exchange(exchange_id)
    markets = exchange.load_markets()
    return sorted(s for s in markets if s.endswith(f"/{quote}"))
