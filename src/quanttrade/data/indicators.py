"""技术指标预处理。

这里把原始 bar 补齐成策略可直接使用的 bar，
避免策略层自己再去重复计算 ATR、ADX 和唐奇安通道。
"""

from __future__ import annotations

from collections import deque

from quanttrade.core.types import MarketBar


def enrich_market_bars(
    bars: list[MarketBar],
    atr_period: int,
    adx_period: int,
    entry_donchian_n: int,
    exit_donchian_m: int,
) -> list[MarketBar]:
    """为原始行情序列补充 ATR、ADX 和唐奇安通道。"""
    if not bars:
        return []

    enriched: list[MarketBar] = []
    previous_close = bars[0].close
    tr_values: list[float] = []
    plus_dm_values: list[float] = []
    minus_dm_values: list[float] = []
    entry_window: deque[float] = deque(maxlen=entry_donchian_n)
    exit_window: deque[float] = deque(maxlen=exit_donchian_m)

    for index, bar in enumerate(bars):
        # True Range 是 ATR 的基础，它反映这一根 bar 的真实波动幅度。
        tr = max(
            bar.high - bar.low,
            abs(bar.high - previous_close),
            abs(bar.low - previous_close),
        )
        up_move = bar.high - bars[index - 1].high if index > 0 else 0.0
        down_move = bars[index - 1].low - bar.low if index > 0 else 0.0
        plus_dm = up_move if up_move > down_move and up_move > 0 else 0.0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0.0

        tr_values.append(tr)
        plus_dm_values.append(plus_dm)
        minus_dm_values.append(minus_dm)

        atr = sum(tr_values[-atr_period:]) / min(len(tr_values), atr_period)
        tr_sum = sum(tr_values[-adx_period:]) or 1.0
        plus_di = 100.0 * sum(plus_dm_values[-adx_period:]) / tr_sum
        minus_di = 100.0 * sum(minus_dm_values[-adx_period:]) / tr_sum
        di_total = plus_di + minus_di
        adx = 100.0 * abs(plus_di - minus_di) / di_total if di_total else 0.0

        # 唐奇安通道在窗口还没凑满之前，先退化成当前 bar 的高低点。
        donchian_high = max(entry_window) if len(entry_window) == entry_donchian_n else bar.high
        donchian_low = min(exit_window) if len(exit_window) == exit_donchian_m else bar.low

        enriched.append(
            MarketBar(
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                atr=round(atr, 4),
                adx=round(adx, 4),
                donchian_high=round(donchian_high, 4),
                donchian_low=round(donchian_low, 4),
            )
        )

        entry_window.append(bar.high)
        exit_window.append(bar.low)
        previous_close = bar.close

    return enriched
