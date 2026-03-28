"""配置数据模型。

这些 dataclass 定义了系统支持哪些配置项，以及每个配置项的默认值。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AppConfig:
    """应用级通用配置。"""

    app_name: str = "QuantTrade"
    environment: str = "dev"


@dataclass(slots=True)
class StrategyConfig:
    """策略参数配置。"""

    name: str = "atr_dtf"
    symbol: str = "AAPL"
    entry_donchian_n: int = 20
    exit_donchian_m: int = 10
    atr_smooth_period: int = 14
    risk_coefficient_k: float = 2.0
    adx_trend_filter: float = 25.0
    risk_pct: float = 0.01
    max_symbol_weight: float = 0.10


@dataclass(slots=True)
class RiskConfig:
    """风控参数配置。"""

    max_daily_drawdown: float = 0.03
    global_max_exposure: float = 0.80
    max_open_positions: int = 5
    slippage_tolerance: float = 0.005
    liquidity_filter: float = 1_000_000.0


@dataclass(slots=True)
class DataConfig:
    """数据层配置。"""

    duckdb_path: str = "var/data/quanttrade.duckdb"
    backend: str = "duckdb"
    timezone: str = "America/New_York"


@dataclass(slots=True)
class NotificationConfig:
    """通知系统配置。"""

    provider: str = "telegram"
    enabled: bool = False
    min_level: str = "warning"
    outbox_path: str = "var/notifications/outbox.jsonl"
    delivery_log_path: str = "var/notifications/delivery-log.jsonl"
    max_delivery_attempts: int = 3
    delivery_retry_backoff_seconds: float = 0.0
    delivery_retry_backoff_strategy: str = "linear"
    delivery_retry_backoff_multiplier: float = 2.0
    max_delivery_retry_backoff_seconds: float = 300.0
    silence_window_seconds: int = 0
    escalation_window_seconds: int = 0
    escalation_min_severity: str = "critical"
    assignment_sla_seconds: int = 0


@dataclass(slots=True)
class ExecutionConfig:
    """执行层配置。"""

    commission_per_order: float = 1.0
    commission_per_share: float = 0.005
    min_commission: float = 1.0
    simulated_slippage_bps: float = 5.0
    max_fill_ratio_per_bar: float = 0.05
    open_order_timeout_bars: int = 2
    max_retry_attempts: int = 2
    retry_backoff_seconds: float = 0.0
    retry_backoff_strategy: str = "linear"
    retry_backoff_multiplier: float = 2.0
    max_retry_backoff_seconds: float = 30.0
    protection_mode_failure_threshold: int = 2
    protection_mode_cooldown_seconds: int = 0
    skip_run_on_protection_mode: bool = True


@dataclass(slots=True)
class Settings:
    """项目完整配置集合。"""

    app: AppConfig = field(default_factory=AppConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    data: DataConfig = field(default_factory=DataConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
