"""风控层基础类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RiskCheckResult:
    """风控校验结果。

    `allowed` 表示是否允许继续下单，
    `reason` 表示如果不允许，究竟是被哪条规则拦下来的。
    """

    allowed: bool
    reason: str
