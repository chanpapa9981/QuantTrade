"""核心异常类型。

这个模块的目标，是把“业务上可预期的失败”从普通 Python 异常里分离出来。
这样运行控制器在决定要不要重试时，就不会只能靠字符串猜测。
"""

from __future__ import annotations


class QuantTradeError(RuntimeError):
    """QuantTrade 领域内的基础异常。"""


class RetryableExecutionError(QuantTradeError):
    """允许运行控制器自动重试的执行异常。

    这类错误通常代表：
    - 某个依赖或状态暂时不稳定；
    - 再试一次大概率可能成功；
    - 继续重试不会立刻带来更大风险。
    """


class NonRetryableExecutionError(QuantTradeError):
    """不应自动重试的执行异常。

    这类错误通常意味着：
    - 输入本身就有问题；
    - 业务规则已经明确不允许继续；
    - 再试只会重复失败或扩大问题。
    """
