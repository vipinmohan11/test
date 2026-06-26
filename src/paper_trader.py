"""Paper-trading ledger: simulates allocating a fixed EUR stake per day
against the live signal, with zero real orders ever placed. Useful for
tracking whether the strategy would have been profitable before risking
real money.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

LEDGER_PATH = Path(__file__).resolve().parent.parent / "data" / "paper_ledger.json"


@dataclass
class PaperPosition:
    date: str
    symbol: str
    stake_eur: float
    entry_price: float
    exit_price: float | None = None
    pnl_eur: float | None = None
    status: str = "OPEN"  # OPEN or CLOSED

    def close(self, exit_price: float, fee_pct: float = 0.1) -> None:
        self.exit_price = exit_price
        gross_pct = (exit_price - self.entry_price) / self.entry_price * 100
        net_pct = gross_pct - (2 * fee_pct)
        self.pnl_eur = round(self.stake_eur * net_pct / 100, 2)
        self.status = "CLOSED"


def _load() -> list[dict]:
    if not LEDGER_PATH.exists():
        return []
    return json.loads(LEDGER_PATH.read_text())


def _save(positions: list[dict]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(positions, indent=2))


def open_position(date: str, symbol: str, stake_eur: float, entry_price: float) -> PaperPosition:
    positions = _load()
    pos = PaperPosition(date=date, symbol=symbol, stake_eur=stake_eur, entry_price=entry_price)
    positions.append(asdict(pos))
    _save(positions)
    return pos


def close_position(date: str, symbol: str, exit_price: float, fee_pct: float = 0.1) -> PaperPosition | None:
    positions = _load()
    for p in positions:
        if p["date"] == date and p["symbol"] == symbol and p["status"] == "OPEN":
            pos = PaperPosition(**p)
            pos.close(exit_price, fee_pct)
            p.update(asdict(pos))
            _save(positions)
            return pos
    return None


def get_ledger() -> list[dict]:
    return _load()


def summary() -> dict:
    positions = _load()
    closed = [p for p in positions if p["status"] == "CLOSED"]
    total_pnl = round(sum(p["pnl_eur"] or 0 for p in closed), 2)
    wins = [p for p in closed if (p["pnl_eur"] or 0) > 0]
    win_rate = round(len(wins) / len(closed) * 100, 1) if closed else 0.0
    return {
        "total_positions": len(positions),
        "open_positions": len(positions) - len(closed),
        "closed_positions": len(closed),
        "total_pnl_eur": total_pnl,
        "win_rate_pct": win_rate,
    }
