"""通知骨架服务。

这个模块当前不直接连 Telegram 等外部服务，而是先完成两件更基础的事情：
1. 统一决定某条告警是该发送、该过滤，还是仅记录；
2. 把可发送的告警写入本地 outbox，作为后续真正对接外部通道的稳定中间层。

这样做的好处是：
- 现在就能验证“系统在关键事件发生时会不会产生日志/告警”；
- 以后要接 Telegram、微信、邮件时，只需要消费 outbox，而不用回头改业务主流程。
"""

from __future__ import annotations

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
