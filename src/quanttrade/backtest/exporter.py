"""结果导出工具。"""

from __future__ import annotations

import json
from pathlib import Path


def export_backtest_result(payload: dict[str, object], output_path: str) -> str:
    """把任意 JSON 结构结果写到磁盘。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)
