from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    HOLD = "hold"
    LONG_ENTRY = "long_entry"
    LONG_EXIT = "long_exit"


class OrderStatus(str, Enum):
    CREATED = "created"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    SKIPPED = "skipped"


@dataclass(slots=True)
class MarketBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    atr: float = 0.0
    adx: float = 0.0
    donchian_high: float = 0.0
    donchian_low: float = 0.0


@dataclass(slots=True)
class PositionState:
    symbol: str
    quantity: int = 0
    entry_price: float = 0.0
    stop_loss: float | None = None
    market_price: float = 0.0

    @property
    def is_open(self) -> bool:
        return self.quantity > 0


@dataclass(slots=True)
class AccountState:
    equity: float
    cash: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    exposure_pct: float = 0.0
    open_positions: int = 0


@dataclass(slots=True)
class StrategyDecision:
    signal: SignalType
    reason: str
    stop_loss: float | None = None
    quantity: int = 0
    metadata: dict[str, float | str] = field(default_factory=dict)


@dataclass(slots=True)
class BacktestMetrics:
    total_return_pct: float
    max_drawdown_pct: float
    longest_underwater_bars: int
    sharpe_ratio: float
    sortino_ratio: float
    win_rate_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_pnl: float
    profit_factor: float
    ending_equity: float


@dataclass(slots=True)
class BacktestRunResult:
    symbol: str
    bars_processed: int
    metrics: BacktestMetrics
    trades: list[dict[str, str | float | int]]
    orders: list[dict[str, str | float | int]]
    audit_log: list[dict[str, str | float | int]]
    account: dict[str, float | int]
    equity_curve: list[dict[str, str | float]]
    drawdown_curve: list[dict[str, str | float]]


@dataclass(slots=True)
class FillEvent:
    timestamp: datetime
    symbol: str
    side: str
    quantity: int
    price: float
    reason: str
    commission: float = 0.0
    gross_value: float = 0.0
    net_value: float = 0.0
    pnl: float = 0.0


@dataclass(slots=True)
class OrderEvent:
    timestamp: datetime
    symbol: str
    side: str
    status: OrderStatus
    quantity: int
    requested_price: float
    filled_quantity: int = 0
    remaining_quantity: int = 0
    fill_price: float = 0.0
    commission: float = 0.0
    gross_value: float = 0.0
    net_value: float = 0.0
    reason: str = ""
