from __future__ import annotations

from pathlib import Path

from quanttrade.config.models import (
    AppConfig,
    DataConfig,
    NotificationConfig,
    RiskConfig,
    Settings,
    StrategyConfig,
)


def _coerce_scalar(value: str) -> object:
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

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        current = stack[-1][1]
        if value == "":
            next_mapping: dict[str, object] = {}
            current[key] = next_mapping
            stack.append((indent, next_mapping))
            continue

        current[key] = _coerce_scalar(value)

    return root


def _section(payload: dict, key: str) -> dict:
    value = payload.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{key}' must be a mapping.")
    return value


def load_settings(path: str | Path) -> Settings:
    config_path = Path(path)
    payload = _parse_simple_yaml(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("Root config must be a mapping.")

    return Settings(
        app=AppConfig(**_section(payload, "app")),
        strategy=StrategyConfig(**_section(payload, "strategy")),
        risk=RiskConfig(**_section(payload, "risk")),
        data=DataConfig(**_section(payload, "data")),
        notification=NotificationConfig(**_section(payload, "notification")),
    )
