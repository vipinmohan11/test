import numpy as np
import pandas as pd

from src.backtest import run_backtest
from src.indicators import add_all_indicators, bollinger_bands, ema, macd, rsi
from src.signals import generate_signal, generate_signal_series


def make_synthetic_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=0.0005, scale=0.01, size=n)
    close = 100 * np.cumprod(1 + returns)
    high = close * (1 + np.abs(rng.normal(0, 0.003, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.003, n)))
    open_ = close * (1 + rng.normal(0, 0.001, n))
    volume = np.abs(rng.normal(1000, 200, n))
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)


def test_indicators_basic_shapes():
    df = make_synthetic_df()
    assert ema(df["close"], 9).shape[0] == len(df)
    r = rsi(df["close"])
    assert r.between(0, 100).all()
    m = macd(df["close"])
    assert {"macd", "signal", "hist"}.issubset(m.columns)
    bb = bollinger_bands(df["close"])
    assert (bb["bb_upper"].dropna() >= bb["bb_mid"].dropna()).all()


def test_add_all_indicators_no_missing_columns():
    df = make_synthetic_df()
    enriched = add_all_indicators(df)
    for col in ["ema_fast", "ema_slow", "rsi", "macd", "signal", "hist", "bb_mid", "bb_upper", "bb_lower", "vol_spike"]:
        assert col in enriched.columns


def test_generate_signal_returns_valid_action():
    df = make_synthetic_df()
    sig = generate_signal(df)
    assert sig.action in {"BUY", "SELL", "HOLD"}
    assert 0 <= sig.confidence <= 100
    assert -1.0 <= sig.score <= 1.0
    assert len(sig.reasons) > 0


def test_generate_signal_series_matches_single_signal():
    df = make_synthetic_df()
    series = generate_signal_series(df)
    single = generate_signal(df)
    assert series["action"].iloc[-1] == single.action


def test_backtest_runs_and_returns_consistent_stats():
    df = make_synthetic_df(n=500)
    result = run_backtest(df, starting_capital=1000.0)
    assert result.num_trades == len(result.trades)
    assert 0 <= result.win_rate_pct <= 100
    if result.num_trades == 0:
        assert result.final_equity == 1000.0


def test_backtest_closes_open_position_at_end():
    df = make_synthetic_df(n=300, seed=1)
    result = run_backtest(df)
    for t in result.trades:
        assert t.exit_price is not None
        assert t.pnl_pct is not None
