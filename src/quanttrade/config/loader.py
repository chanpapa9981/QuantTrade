"""配置加载器。

项目当前为了尽量减少外部依赖，先实现了一个“够用”的简化 YAML 解析器。
它不追求完整 YAML 语法，而是支持本项目现阶段所需的键值和层级结构。
"""

from __future__ import annotations

from pathlib import Path

from quanttrade.config.models import (
    AppConfig,
    BrokerConfig,
    DataConfig,
    ExecutionConfig,
    LiveConfig,
    NotificationConfig,
    RiskConfig,
    Settings,
    StrategyConfig,
)


def _coerce_scalar(value: str) -> object:
    """把 YAML 文本里的标量值转成 Python 类型。

    例如：
    - `"true"` -> `True`
    - `"12"` -> `12`
    - `"1.5"` -> `1.5`
    - `"null"` -> `None`
    """
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_simple_yaml(text: str) -> dict:
    """解析项目使用的简化 YAML。

    这里使用缩进栈来追踪当前所处的层级。
    对小白来说，可以把 `stack` 理解成“当前正在往哪一层字典里写内容”的记录表。
    """
    root: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-1, root)]

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            raise ValueError(f"Invalid config line: {raw_line}")

        key, _, raw_value = line.partition(":")
        key = key.strip()
        value = raw_value.strip()

        # 如果当前行缩进变浅，说明前一个子层级已经结束，需要退回到更上层。
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        current = stack[-1][1]
        if value == "":
            # 没有值时，说明这是一个新的嵌套 section，例如 `strategy:`。
            next_mapping: dict[str, object] = {}
            current[key] = next_mapping
            stack.append((indent, next_mapping))
            continue

        current[key] = _coerce_scalar(value)

    return root


def _section(payload: dict, key: str) -> dict:
    """安全地取出某个配置分组，并确保它的确是字典。"""
    value = payload.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{key}' must be a mapping.")
    return value


def load_settings(path: str | Path) -> Settings:
    """从 YAML 文件加载完整 Settings 对象。"""
    config_path = Path(path)
    payload = _parse_simple_yaml(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("Root config must be a mapping.")

    return Settings(
        app=AppConfig(**_section(payload, "app")),
        strategy=StrategyConfig(**_section(payload, "strategy")),
        risk=RiskConfig(**_section(payload, "risk")),
        data=DataConfig(**_section(payload, "data")),
        execution=ExecutionConfig(**_section(payload, "execution")),
        live=LiveConfig(**_section(payload, "live")),
        broker=BrokerConfig(**_section(payload, "broker")),
        notification=NotificationConfig(**_section(payload, "notification")),
    )
