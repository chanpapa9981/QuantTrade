"""核心领域类型定义。

这份文件定义的是系统各个模块之间共享的“共同语言”。
如果把项目比作工厂，这里就是统一的零件规格书。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    """策略层发出的动作信号。"""

    HOLD = "hold"
    LONG_ENTRY = "long_entry"
    LONG_EXIT = "long_exit"


class OrderStatus(str, Enum):
    """订单在执行过程中的状态枚举。"""

    CREATED = "created"
    OPEN = "open"
    REPLACED = "replaced"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    SKIPPED = "skipped"


@dataclass(slots=True)
class MarketBar:
    """一根标准化行情 bar。

    除了原始 OHLCV，这里还会挂上预计算出来的 ATR、ADX、唐奇安通道等指标，
    这样策略层就能直接读取，不需要自己重复算。
    """

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
    """当前持仓状态。"""

    symbol: str
    quantity: int = 0
    entry_price: float = 0.0
    stop_loss: float | None = None
    market_price: float = 0.0

    @property
    def is_open(self) -> bool:
        """只要持仓数量大于 0，就认为当前有持仓。"""
        return self.quantity > 0


@dataclass(slots=True)
class AccountState:
    """账户状态快照。"""

    equity: float
    cash: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    exposure_pct: float = 0.0
    open_positions: int = 0


@dataclass(slots=True)
class StrategyDecision:
    """策略输出的标准决策对象。"""

    signal: SignalType
    reason: str
    stop_loss: float | None = None
    quantity: int = 0
    metadata: dict[str, float | str] = field(default_factory=dict)


@dataclass(slots=True)
class BacktestMetrics:
    """回测最终汇总出来的绩效指标。"""

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
    """一次完整回测的最终输出。"""

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
    """真实成交事件。

    注意它和订单事件不同：
    - 订单事件描述“订单状态变了什么”；
    - 成交事件描述“到底成交了多少、多少钱、盈亏多少”。
    """

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
class PendingOrderState:
    """跨 bar 持续存在的挂单状态。"""

    order_id: str
    symbol: str
    side: str
    requested_quantity: int
    remaining_quantity: int
    reason: str
    requested_price: float
    submitted_at: datetime
    stop_loss: float | None = None
    bars_open: int = 0


@dataclass(slots=True)
class OrderEvent:
    """订单事件。

    每次订单创建、挂起、改价、部分成交、完全成交、取消、拒绝，
    都会沉淀成一条事件，供后续查询和审计。
    """

    timestamp: datetime
    order_id: str
    symbol: str
    side: str
    status: OrderStatus
    quantity: int
    requested_price: float
    filled_quantity: int = 0
    remaining_quantity: int = 0
    broker_status: str = ""
    status_detail: str = ""
    fill_price: float = 0.0
    commission: float = 0.0
    gross_value: float = 0.0
    net_value: float = 0.0
    reason: str = ""
