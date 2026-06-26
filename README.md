# Crypto Day-Trading Signal Dashboard

A Streamlit dashboard that fetches live OHLCV candles from Binance,
Coinbase, or Kraken, computes technical indicators (EMA crossover, RSI,
MACD, Bollinger Bands, volume spikes), and turns them into a heuristic
BUY/SELL/HOLD signal with a confidence score. Includes a backtester and
a paper-trading ledger that simulates allocating a fixed EUR stake per
day -- no real orders are ever placed.

## Disclaimer

This is an educational technical-analysis tool, **not** a prediction
engine and **not** financial advice. No software can reliably predict
short-term crypto price movement. Backtest results reflect the past,
not the future. Trade only with money you can afford to lose.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project layout

- `src/data_feed.py` -- unified OHLCV fetching across exchanges via `ccxt`
- `src/indicators.py` -- EMA, RSI, MACD, Bollinger Bands, volume spike (pure pandas)
- `src/signals.py` -- combines indicators into a weighted BUY/SELL/HOLD signal
- `src/backtest.py` -- replays the signal strategy over historical candles
- `src/paper_trader.py` -- simulated EUR-stake ledger, persisted to `data/paper_ledger.json`
- `app.py` -- Streamlit UI
- `tests/` -- pytest suite using synthetic OHLCV data

## Running tests

```bash
pip install pytest
pytest tests/
```
