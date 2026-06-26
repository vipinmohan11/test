"""Technical indicators computed with pandas only (no external TA dependency)."""
from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": histogram})


def bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return pd.DataFrame({"bb_mid": mid, "bb_upper": upper, "bb_lower": lower})


def volume_spike(volume: pd.Series, period: int = 20, multiplier: float = 2.0) -> pd.Series:
    avg_volume = volume.rolling(period).mean()
    return volume > (avg_volume * multiplier)


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with all indicator columns appended."""
    out = df.copy()
    out["ema_fast"] = ema(out["close"], 9)
    out["ema_slow"] = ema(out["close"], 21)
    out["rsi"] = rsi(out["close"])
    macd_df = macd(out["close"])
    out = out.join(macd_df)
    bb_df = bollinger_bands(out["close"])
    out = out.join(bb_df)
    out["vol_spike"] = volume_spike(out["volume"])
    return out
