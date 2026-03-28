"""券商只读同步骨架。

当前阶段先不直接接真实 Schwab API，而是先把“券商快照长什么样、同步结果怎么统一表示”
这一层搭起来。这样后面真正接 OAuth / HTTP client 时，可以直接替换 provider 适配逻辑，
不用回头重做上层 repository、CLI 和 history 视图。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from quanttrade.config.models import BrokerConfig
from quanttrade.core.types import BrokerAccountSnapshot, BrokerOrderSnapshot, BrokerPositionSnapshot


def _load_json_payload(path: str) -> object:
    """读取本地 JSON 快照文件。

    本地文件 provider 的意义不是偷懒，而是先把“外部快照同步”这件事做成可测试骨架：
    - 现在可以用 fixture 文件反复验证同步逻辑；
    - 以后接真实 broker 时，把这里换成 HTTP 拉取即可。
    """
    snapshot_path = Path(path)
    if not snapshot_path.exists():
        raise FileNotFoundError(f"broker snapshot file does not exist: {snapshot_path}")
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def _normalize_account_snapshot(payload: object) -> BrokerAccountSnapshot:
    """把外部账户 JSON 整理成统一结构。"""
    data = payload if isinstance(payload, dict) else {}
    return BrokerAccountSnapshot(
        account_id=str(data.get("account_id", "")),
        currency=str(data.get("currency", "USD")),
        equity=float(data.get("equity", 0.0) or 0.0),
        cash=float(data.get("cash", 0.0) or 0.0),
        buying_power=float(data.get("buying_power", 0.0) or 0.0),
        source_updated_at=str(data.get("source_updated_at", "")),
    )


def _normalize_position_snapshots(payload: object) -> list[BrokerPositionSnapshot]:
    """把外部持仓列表整理成统一结构。"""
    rows = payload if isinstance(payload, list) else []
    snapshots: list[BrokerPositionSnapshot] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        snapshots.append(
            BrokerPositionSnapshot(
                symbol=str(row.get("symbol", "")),
                quantity=float(row.get("quantity", 0.0) or 0.0),
                market_price=float(row.get("market_price", 0.0) or 0.0),
                average_cost=float(row.get("average_cost", 0.0) or 0.0),
                market_value=float(row.get("market_value", 0.0) or 0.0),
                unrealized_pnl=float(row.get("unrealized_pnl", 0.0) or 0.0),
                source_updated_at=str(row.get("source_updated_at", "")),
            )
        )
    return snapshots


def _normalize_order_snapshots(payload: object) -> list[BrokerOrderSnapshot]:
    """把外部订单列表整理成统一结构。"""
    rows = payload if isinstance(payload, list) else []
    snapshots: list[BrokerOrderSnapshot] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        snapshots.append(
            BrokerOrderSnapshot(
                broker_order_id=str(row.get("broker_order_id", "")),
                symbol=str(row.get("symbol", "")),
                side=str(row.get("side", "")),
                status=str(row.get("status", "")),
                quantity=float(row.get("quantity", 0.0) or 0.0),
                filled_quantity=float(row.get("filled_quantity", 0.0) or 0.0),
                limit_price=float(row.get("limit_price", 0.0) or 0.0),
                stop_price=float(row.get("stop_price", 0.0) or 0.0),
                submitted_at=str(row.get("submitted_at", "")),
                source_updated_at=str(row.get("source_updated_at", "")),
            )
        )
    return snapshots


def fetch_broker_snapshot(config: BrokerConfig) -> dict[str, object]:
    """读取并标准化一份券商快照。

    返回结果保持纯字典，方便 repository / CLI / history 直接消费。
    """
    provider = str(config.provider or "").strip().lower()
    if provider != "local_file":
        raise ValueError(f"unsupported broker provider in current stage: {config.provider}")

    account = _normalize_account_snapshot(_load_json_payload(config.account_snapshot_path))
    positions = _normalize_position_snapshots(_load_json_payload(config.positions_snapshot_path))
    orders = _normalize_order_snapshots(_load_json_payload(config.orders_snapshot_path))
    synced_at = datetime.now(timezone.utc).isoformat()
    return {
        "provider": config.provider,
        "synced_at": synced_at,
        "account": asdict(account),
        "positions": [asdict(item) for item in positions],
        "orders": [asdict(item) for item in orders],
    }
