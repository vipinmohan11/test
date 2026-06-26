"""Crypto day-trading signal dashboard.

Shows live price + indicators, a heuristic buy/sell/hold signal, a
backtest of that strategy, and a paper-trading ledger that simulates
allocating a fixed EUR stake per day -- with ZERO real orders ever sent
to an exchange.

DISCLAIMER: This tool produces technical-indicator-based heuristics, not
guaranteed predictions. Cryptocurrency markets are highly volatile and
no model can reliably predict short-term price movement. Nothing here
is financial advice. Past backtest performance does not guarantee future
results. Only trade with money you can afford to lose.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.backtest import run_backtest
from src.data_feed import fetch_ohlcv
from src.indicators import add_all_indicators
from src.paper_trader import close_position, get_ledger, open_position, summary
from src.signals import generate_signal

st.set_page_config(page_title="Crypto Signal Dashboard", layout="wide")

st.title("Crypto Day-Trading Signal Dashboard")
st.warning(
    "⚠️ Educational tool only. Signals are heuristic technical-indicator "
    "combinations, **not** guaranteed predictions. This is not financial "
    "advice. Crypto is highly volatile -- never risk money you can't afford "
    "to lose."
)

with st.sidebar:
    st.header("Settings")
    exchange_id = st.selectbox("Exchange", ["binance", "coinbase", "kraken"])
    symbol = st.text_input("Symbol (ccxt format)", value="BTC/EUR")
    timeframe = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"], index=1)
    candles = st.slider("Candles to load", 100, 1000, 300, step=50)
    daily_stake = st.number_input("Daily stake (EUR)", min_value=10.0, value=1000.0, step=50.0)
    fee_pct = st.number_input("Per-side fee (%)", min_value=0.0, value=0.1, step=0.05)
    refresh = st.button("Refresh data")

try:
    df = fetch_ohlcv(exchange_id, symbol, timeframe=timeframe, limit=candles)
except Exception as exc:
    st.error(f"Failed to fetch data from {exchange_id} for {symbol}: {exc}")
    st.stop()

enriched = add_all_indicators(df)
signal = generate_signal(df)
last_price = df["close"].iloc[-1]

col1, col2, col3 = st.columns(3)
col1.metric("Last price", f"{last_price:,.2f}")
action_color = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}[signal.action]
col2.metric("Signal", f"{action_color} {signal.action}", f"confidence {signal.confidence}%")
col3.metric("Score", f"{signal.score:+.2f}")

with st.expander("Why this signal?"):
    for reason in signal.reasons:
        st.write(f"- {reason}")

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=enriched.index, open=enriched["open"], high=enriched["high"],
    low=enriched["low"], close=enriched["close"], name="Price",
))
fig.add_trace(go.Scatter(x=enriched.index, y=enriched["ema_fast"], name="EMA9", line=dict(width=1)))
fig.add_trace(go.Scatter(x=enriched.index, y=enriched["ema_slow"], name="EMA21", line=dict(width=1)))
fig.add_trace(go.Scatter(x=enriched.index, y=enriched["bb_upper"], name="BB Upper", line=dict(width=1, dash="dot")))
fig.add_trace(go.Scatter(x=enriched.index, y=enriched["bb_lower"], name="BB Lower", line=dict(width=1, dash="dot")))
fig.update_layout(height=500, xaxis_rangeslider_visible=False, margin=dict(t=20, b=20))
st.plotly_chart(fig, use_container_width=True)

rsi_col, macd_col = st.columns(2)
with rsi_col:
    rsi_fig = go.Figure(go.Scatter(x=enriched.index, y=enriched["rsi"], name="RSI"))
    rsi_fig.add_hline(y=70, line_dash="dash", line_color="red")
    rsi_fig.add_hline(y=30, line_dash="dash", line_color="green")
    rsi_fig.update_layout(height=250, title="RSI", margin=dict(t=30, b=20))
    st.plotly_chart(rsi_fig, use_container_width=True)
with macd_col:
    macd_fig = go.Figure()
    macd_fig.add_trace(go.Bar(x=enriched.index, y=enriched["hist"], name="Histogram"))
    macd_fig.add_trace(go.Scatter(x=enriched.index, y=enriched["macd"], name="MACD"))
    macd_fig.add_trace(go.Scatter(x=enriched.index, y=enriched["signal"], name="Signal"))
    macd_fig.update_layout(height=250, title="MACD", margin=dict(t=30, b=20))
    st.plotly_chart(macd_fig, use_container_width=True)

st.divider()
st.subheader("Backtest this strategy")
backtest_capital = st.number_input("Backtest starting capital (EUR)", min_value=10.0, value=1000.0, step=50.0)
result = run_backtest(df, starting_capital=backtest_capital, fee_pct=fee_pct)
b1, b2, b3, b4 = st.columns(4)
b1.metric("Total return", f"{result.total_return_pct:+.2f}%")
b2.metric("Win rate", f"{result.win_rate_pct}%")
b3.metric("Trades", result.num_trades)
b4.metric("Final equity", f"{result.final_equity:,.2f}")
st.caption(
    "Backtest covers only the loaded candle window above. More history "
    "(increase 'Candles to load') gives a more meaningful sample, but "
    "still reflects the past, not the future."
)

if result.trades:
    trades_df = pd.DataFrame([
        {
            "entry_time": t.entry_time, "entry_price": t.entry_price,
            "exit_time": t.exit_time, "exit_price": t.exit_price,
            "pnl_pct": round(t.pnl_pct, 2) if t.pnl_pct is not None else None,
        }
        for t in result.trades
    ])
    st.dataframe(trades_df, use_container_width=True)

st.divider()
st.subheader("Paper trading ledger (simulated only -- no real orders)")
st.caption(f"Allocates {daily_stake:.0f} EUR notionally per BUY signal and tracks hypothetical P&L.")

ledger_col1, ledger_col2 = st.columns(2)
with ledger_col1:
    if st.button(f"Record paper {signal.action} @ {last_price:,.2f}", disabled=signal.action == "HOLD"):
        today = dt.date.today().isoformat()
        if signal.action == "BUY":
            open_position(today, symbol, daily_stake, last_price)
            st.success(f"Recorded paper BUY of {symbol} for {daily_stake} EUR @ {last_price:,.2f}")
        elif signal.action == "SELL":
            closed = close_position(today, symbol, last_price, fee_pct)
            if closed:
                st.success(f"Closed paper position: PnL {closed.pnl_eur:+.2f} EUR")
            else:
                st.info("No open paper position to close for today/symbol.")

ledger = get_ledger()
if ledger:
    st.dataframe(pd.DataFrame(ledger), use_container_width=True)
    stats = summary()
    s1, s2, s3 = st.columns(3)
    s1.metric("Total P&L (EUR)", f"{stats['total_pnl_eur']:+.2f}")
    s2.metric("Closed positions", stats["closed_positions"])
    s3.metric("Win rate", f"{stats['win_rate_pct']}%")
else:
    st.info("No paper trades recorded yet.")
