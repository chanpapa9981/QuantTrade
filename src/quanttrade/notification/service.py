"""通知骨架服务。

这个模块现在负责三层能力：
1. 判断某条事件是否应该进入通知流程；
2. 把待发送事件写进本地 outbox，形成稳定的“待投递队列”；
3. 用一个本地 adapter 骨架把队列里的事件继续写入 delivery log，模拟后续真正的外部投递工人。

注意这里还没有真正接 Telegram/微信 API。
当前 delivery log 的含义是：
- worker 已经接手并尝试把这条通知交给“渠道适配层”；
- 方便以后替换成真实 provider，而不用回头改业务主流程。
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from quanttrade.config.models import NotificationConfig

_LEVEL_RANK = {
    "info": 10,
    "warning": 20,
    "error": 30,
    "critical": 40,
}


def should_emit_notification(config: NotificationConfig, severity: str) -> bool:
    """判断某条告警是否达到了当前配置允许进入 outbox 的最低级别。"""
    current_level = _LEVEL_RANK.get(str(severity).strip().lower(), 20)
    min_level = _LEVEL_RANK.get(str(config.min_level).strip().lower(), 20)
    return current_level >= min_level


def append_notification_to_outbox(config: NotificationConfig, payload: dict[str, object]) -> str:
    """把通知事件追加写入本地 JSONL outbox。

    JSONL 的好处是：
    - 每一行都是一条独立事件，后续很适合被脚本或守护进程流式消费；
    - 即使文件很大，也不需要每次整文件重写。
    """
    path = Path(config.outbox_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return str(path)


def dispatch_notification_via_adapter(config: NotificationConfig, payload: dict[str, object]) -> str:
    """把一条通知交给当前阶段的本地 adapter 骨架。

    这里故意不假装“真的发到了 Telegram”，而是把 adapter 接手后的结果写入 delivery log。
    这样做的价值在于：
    - 我们已经能测试 worker 是否会正确处理 queued 通知；
    - 以后替换成真实 provider 时，只需要替换这一个适配点。

    为了让测试能覆盖失败重试路径，这里保留 `failing_stub` provider：
    - 当配置成 `failing_stub` 时，adapter 会稳定抛错；
    - 这样可以测试 worker 如何记录失败、递增尝试次数，并最终停止重投。
    """
    provider = str(config.provider).strip().lower()
    if provider == "failing_stub":
        raise RuntimeError("simulated notification adapter failure")

    path = Path(config.delivery_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    adapter_record = {
        **payload,
        "adapter_provider": config.provider,
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(adapter_record, ensure_ascii=False) + "\n")
    return str(path)
