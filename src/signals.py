"""Rule-based buy/sell/hold signal generation from technical indicators.

This is a heuristic scoring system, not a guarantee of future price movement.
Crypto markets are highly volatile; treat signals as one input among many,
never as financial advice.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.indicators import add_all_indicators

BUY_THRESHOLD = 0.35
SELL_THRESHOLD = -0.35


@dataclass
class Signal:
    action: str  # "BUY", "SELL", or "HOLD"
    score: float  # raw weighted score in [-1, 1]
    confidence: float  # 0-100, abs(score) scaled
    reasons: list[str]


def _row_score(row: pd.Series) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    # Trend: EMA crossover (weight 0.3)
    if row["ema_fast"] > row["ema_slow"]:
        score += 0.3
        reasons.append("EMA9 above EMA21 (uptrend)")
    else:
        score -= 0.3
        reasons.append("EMA9 below EMA21 (downtrend)")

    # Momentum: RSI (weight 0.25)
    if row["rsi"] < 30:
        score += 0.25
        reasons.append(f"RSI oversold ({row['rsi']:.1f})")
    elif row["rsi"] > 70:
        score -= 0.25
        reasons.append(f"RSI overbought ({row['rsi']:.1f})")

    # MACD histogram (weight 0.25)
    if row["hist"] > 0:
        score += 0.25
        reasons.append("MACD histogram positive")
    else:
        score -= 0.25
        reasons.append("MACD histogram negative")

    # Bollinger Bands mean reversion (weight 0.2)
    if row["close"] <= row["bb_lower"]:
        score += 0.2
        reasons.append("Price at/below lower Bollinger Band")
    elif row["close"] >= row["bb_upper"]:
        score -= 0.2
        reasons.append("Price at/above upper Bollinger Band")

    # Volume spike amplifies whichever direction the move already points
    if row.get("vol_spike"):
        score *= 1.15
        reasons.append("Volume spike confirms move")

    score = max(-1.0, min(1.0, score))
    return score, reasons


def generate_signal(df: pd.DataFrame) -> Signal:
    """Compute indicators and produce a single signal for the latest candle."""
    enriched = add_all_indicators(df)
    latest = enriched.iloc[-1]
    score, reasons = _row_score(latest)

    if score >= BUY_THRESHOLD:
        action = "BUY"
    elif score <= SELL_THRESHOLD:
        action = "SELL"
    else:
        action = "HOLD"

    return Signal(action=action, score=score, confidence=round(abs(score) * 100, 1), reasons=reasons)


def generate_signal_series(df: pd.DataFrame) -> pd.DataFrame:
    """Compute a signal for every candle (used by the backtester)."""
    enriched = add_all_indicators(df)
    scores = enriched.apply(_row_score, axis=1, result_type="expand")
    enriched["score"] = scores[0]
    enriched["action"] = enriched["score"].apply(
        lambda s: "BUY" if s >= BUY_THRESHOLD else ("SELL" if s <= SELL_THRESHOLD else "HOLD")
    )
    return enriched
