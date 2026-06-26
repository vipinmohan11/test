"""Backtest the signal strategy over historical OHLCV data.

Simulates a single open position at a time: enters fully on BUY,
exits fully on SELL, ignores HOLD. No leverage, no fees beyond the
configurable taker fee estimate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.signals import generate_signal_series


@dataclass
class Trade:
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp | None = None
    exit_price: float | None = None

    @property
    def pnl_pct(self) -> float | None:
        if self.exit_price is None:
            return None
        return (self.exit_price - self.entry_price) / self.entry_price * 100


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    total_return_pct: float = 0.0
    win_rate_pct: float = 0.0
    num_trades: int = 0
    final_equity: float = 0.0


def run_backtest(df: pd.DataFrame, starting_capital: float = 1000.0, fee_pct: float = 0.1) -> BacktestResult:
    enriched = generate_signal_series(df)

    equity = starting_capital
    position: Trade | None = None
    trades: list[Trade] = []

    for ts, row in enriched.iterrows():
        action = row["action"]
        price = row["close"]

        if position is None and action == "BUY":
            position = Trade(entry_time=ts, entry_price=price)
        elif position is not None and action == "SELL":
            position.exit_time = ts
            position.exit_price = price
            gross_pnl_pct = position.pnl_pct
            net_pnl_pct = gross_pnl_pct - (2 * fee_pct)
            equity *= 1 + (net_pnl_pct / 100)
            trades.append(position)
            position = None

    if position is not None:
        last_price = enriched["close"].iloc[-1]
        position.exit_time = enriched.index[-1]
        position.exit_price = last_price
        net_pnl_pct = position.pnl_pct - (2 * fee_pct)
        equity *= 1 + (net_pnl_pct / 100)
        trades.append(position)

    wins = [t for t in trades if (t.pnl_pct or 0) > 0]
    win_rate = (len(wins) / len(trades) * 100) if trades else 0.0
    total_return = (equity - starting_capital) / starting_capital * 100

    return BacktestResult(
        trades=trades,
        total_return_pct=round(total_return, 2),
        win_rate_pct=round(win_rate, 1),
        num_trades=len(trades),
        final_equity=round(equity, 2),
    )
